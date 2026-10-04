#!/usr/bin/env python3
"""After a deploy, probe the live receiver and write worker/deploy_check.json.

Sends only harmless requests: a health check, three messages that must be rejected, and an authorised read of the queue
(limit 1). The drain token is read from the environment and is never written to the result. Standard library only."""
import datetime, json, os, re, urllib.error, urllib.request

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "deploy_check.json")
PERMIT = "arn:aws:sns:eu-west-2:287813576808:prod-permit-topic"

def call(url, method="GET", data=None, headers=None):
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace")[:300]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:300]
    except Exception as e:
        return None, str(e)[:200]

def main():
    res = {"checkedAt": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "deployOutcome": os.environ.get("DEPLOYED") or "skipped"}
    url = (os.environ.get("URL") or "").strip()
    if not url:
        m = re.search(r"https://[A-Za-z0-9.-]+\.workers\.dev", os.environ.get("OUT") or "")
        url = m.group(0) if m else ""
    if res["deployOutcome"] != "success" or not url:
        res["note"] = "Not deployed (the three repository secrets may be missing, or the deploy failed): nothing to probe."
        res["allPassed"] = False
    else:
        url = url.rstrip("/"); res["url"] = url
        token = os.environ.get("DRAIN") or ""
        fake = json.dumps({"Type": "Notification", "TopicArn": PERMIT, "Message": "{}", "MessageId": "x", "Timestamp": "t",
                           "SignatureVersion": "1", "Signature": "AAAA", "SigningCertURL": "https://sns.eu-west-2.amazonaws.com/x.pem"}).encode()
        c = {
            "health": call(url + "/health"),
            "wrong_topic_rejected": call(url + "/permit", "POST", b'{"TopicArn":"nope"}', {"content-type": "text/plain"}),
            "unsigned_message_rejected": call(url + "/permit", "POST", fake, {"content-type": "text/plain"}),
            "drain_without_token_rejected": call(url + "/drain"),
            "drain_with_token": call(url + "/drain?limit=1", "GET", None, {"authorization": "Bearer " + token}),
        }
        res["checks"] = {k: {"status": v[0], "body": v[1]} for k, v in c.items()}
        res["allPassed"] = (c["health"][0] == 200 and c["wrong_topic_rejected"][0] == 403 and c["unsigned_message_rejected"][0] == 403
                            and c["drain_without_token_rejected"][0] == 401 and c["drain_with_token"][0] == 200)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    print(json.dumps({k: res[k] for k in ("deployOutcome", "allPassed")}))

if __name__ == "__main__":
    main()
