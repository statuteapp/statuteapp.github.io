// Amazon SNS message checks, using only web-standard APIs (works in Cloudflare Workers and in Node for tests).
// DfT's Street Manager open data arrives as Amazon SNS messages. Every message is checked before it is trusted:
// the topic must be one of DfT's three, the signing certificate must come from an Amazon SNS address, and the RSA
// signature over the message fields must verify.

export const TOPICS = {
  permit: "arn:aws:sns:eu-west-2:287813576808:prod-permit-topic",
  activity: "arn:aws:sns:eu-west-2:287813576808:prod-activity-topic",
  section58: "arn:aws:sns:eu-west-2:287813576808:prod-section-58-topic",
};

const SNS_HOST = /^sns\.[a-z0-9-]+\.amazonaws\.com(\.cn)?$/;

function snsUrl(u, suffix) {
  try {
    const x = new URL(u);
    return x.protocol === "https:" && SNS_HOST.test(x.hostname) && !x.username && !x.password && (x.port === "" || x.port === "443") && (!suffix || x.pathname.endsWith(suffix));
  } catch (e) {
    return false;
  }
}
export const certUrlOk = (u) => snsUrl(u, ".pem");
export const subscribeUrlOk = (u) => snsUrl(u, "");

// The exact text Amazon signs: "Name\nValue\n" for each present field, in this order (per Amazon's SNS documentation).
export function stringToSign(m) {
  const keys = m.Type === "Notification"
    ? ["Message", "MessageId", "Subject", "Timestamp", "TopicArn", "Type"]
    : ["Message", "MessageId", "SubscribeURL", "Timestamp", "Token", "TopicArn", "Type"];
  return keys.filter((k) => m[k] !== undefined && m[k] !== null).map((k) => k + "\n" + m[k] + "\n").join("");
}

function tlv(b, o) {
  const tag = b[o];
  let len = b[o + 1], h = 2;
  if (len & 0x80) {
    const n = len & 0x7f;
    len = 0;
    for (let i = 0; i < n; i++) len = len * 256 + b[o + 2 + i];
    h = 2 + n;
  }
  return { tag, start: o, body: o + h, end: o + h + len };
}

// Pull the public key (SubjectPublicKeyInfo) out of an X.509 certificate in DER form.
export function spkiFromCertDer(der) {
  const cert = tlv(der, 0);
  const tbs = tlv(der, cert.body);
  let o = tbs.body;
  if (tlv(der, o).tag === 0xa0) o = tlv(der, o).end;           // optional version
  for (let i = 0; i < 5; i++) o = tlv(der, o).end;             // serial, signature algorithm, issuer, validity, subject
  const spki = tlv(der, o);
  return der.slice(spki.start, spki.end);
}

const certCache = new Map();
export async function fetchCertPem(url) {
  if (certCache.has(url)) return certCache.get(url);
  const r = await fetch(url);
  if (!r.ok) throw new Error("certificate fetch " + r.status);
  const pem = await r.text();
  if (certCache.size > 20) certCache.clear();
  certCache.set(url, pem);
  return pem;
}

const bytesFromB64 = (s) => Uint8Array.from(atob(s), (c) => c.charCodeAt(0));

export async function verifySns(m, getCertPem = fetchCertPem) {
  try {
    if (!certUrlOk(m.SigningCertURL)) return false;
    const v = String(m.SignatureVersion);
    const hash = v === "1" ? "SHA-1" : v === "2" ? "SHA-256" : null;
    if (!hash || typeof m.Signature !== "string") return false;
    const pem = await getCertPem(m.SigningCertURL);
    const der = bytesFromB64(pem.replace(/-----[^-]+-----/g, "").replace(/\s+/g, ""));
    const key = await crypto.subtle.importKey("spki", spkiFromCertDer(der), { name: "RSASSA-PKCS1-v1_5", hash }, false, ["verify"]);
    return await crypto.subtle.verify("RSASSA-PKCS1-v1_5", key, bytesFromB64(m.Signature), new TextEncoder().encode(stringToSign(m)));
  } catch (e) {
    return false;
  }
}
