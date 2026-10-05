// What happens to Amazon's subscription and notification messages on a deployed Worker (found from Cloudflare's logs on 5 October 2026).
// The Worker once answered every real Amazon message with a 500: its default settings handed Cloudflare's fetch to the code as a method of
// another object, and Cloudflare refuses that ("Illegal invocation"). The fake fetch the other tests pass in could never show it.
// Same helpers as receiver.test.mjs (a throwaway key and certificate stand in for Amazon's).
import test from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { createSign } from "node:crypto";
import { mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { handle } from "../src/index.js";
import { TOPICS } from "../src/sns.js";

// A throwaway key and certificate stand in for Amazon's.
const dir = mkdtempSync(join(tmpdir(), "sns-"));
execFileSync("openssl", ["req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", join(dir, "k.pem"), "-out", join(dir, "c.pem"), "-subj", "/CN=sns.test", "-days", "2"], { stdio: "ignore" });
const KEY = readFileSync(join(dir, "k.pem"), "utf8"), CERT = readFileSync(join(dir, "c.pem"), "utf8");
const CERT_URL = "https://sns.eu-west-2.amazonaws.com/SimpleNotificationService-test.pem";
const deps = (extra = {}) => ({ getCert: async () => CERT, fetch: async () => ({ ok: true }), ...extra });

const EVENT = { event_reference: 165000001, event_type: "PERMIT_GRANTED", object_type: "PERMIT", object_reference: "W1-01", event_time: "2026-10-04T10:00:00.000Z", object_data: { work_reference_number: "W1", street_name: "HIGH STREET" } };

// Written out by hand from Amazon's documented format, independently of src/sns.js.
function signed(over = {}, version = "1") {
  const m = { Type: "Notification", MessageId: "11111111-2222-3333-4444-555555555555", TopicArn: TOPICS.permit, Message: JSON.stringify(EVENT), Timestamp: "2026-10-04T10:00:01.000Z", SignatureVersion: version, SigningCertURL: CERT_URL, ...over };
  let s;
  if (m.Type === "Notification") s = `Message\n${m.Message}\nMessageId\n${m.MessageId}\n${m.Subject ? "Subject\n" + m.Subject + "\n" : ""}Timestamp\n${m.Timestamp}\nTopicArn\n${m.TopicArn}\nType\n${m.Type}\n`;
  else s = `Message\n${m.Message}\nMessageId\n${m.MessageId}\nSubscribeURL\n${m.SubscribeURL}\nTimestamp\n${m.Timestamp}\nToken\n${m.Token}\nTopicArn\n${m.TopicArn}\nType\n${m.Type}\n`;
  m.Signature = createSign(version === "1" ? "RSA-SHA1" : "RSA-SHA256").update(s).sign(KEY, "base64");
  return m;
}

function fakeDB() {
  const rows = [], subs = [];
  return { rows, subs, prepare(sql) { return { bind(...a) { return {
    async run() {
      if (/^INSERT INTO subs/i.test(sql)) { subs.push({ topic: a[0], at: a[1], ok: a[2], note: a[3] }); return { meta: { changes: 1 } }; }
      if (/^INSERT/i.test(sql)) { const id = (rows.length ? Math.max(...rows.map((r) => r.id)) : 0) + 1; rows.push({ id, topic: a[0], at: a[1], body: a[2] }); return { meta: { changes: 1 } }; }
      if (/^DELETE/i.test(sql)) { const max = Math.max(...rows.map((r) => r.id)); const keep = rows.filter((r) => !(r.id <= a[0] && r.id < max)); const n = rows.length - keep.length; rows.length = 0; rows.push(...keep); return { meta: { changes: n } }; }
    },
    async all() { return { results: rows.filter((r) => r.id > a[0]).sort((x, y) => x.id - y.id).slice(0, a[1]) }; },
  }; } }; } };
}
const post = (path, body, headers = {}) => new Request("https://r.test" + path, { method: "POST", body: typeof body === "string" ? body : JSON.stringify(body), headers });
const env = (db, token = "secret-token") => ({ DB: db, DRAIN_TOKEN: token });


test("with the default settings the confirmation call uses fetch the way Cloudflare requires (no borrowed 'this')", async () => {
  const real = globalThis.fetch, called = [];
  globalThis.fetch = function (u) {
    if (this !== undefined && this !== globalThis) throw new TypeError("Illegal invocation: function called with incorrect `this` reference");
    called.push(String(u));
    return Promise.resolve(String(u).endsWith(".pem") ? { ok: true, status: 200, text: async () => CERT } : { ok: true, status: 200 });
  };
  try {
    const conf = signed({ Type: "SubscriptionConfirmation", Token: "t", Message: "m", SubscribeURL: "https://sns.eu-west-2.amazonaws.com/?Action=ConfirmSubscription&Token=t" });
    const db = fakeDB(); const r = await handle(post("/permit", conf), env(db));          // no settings passed: the defaults a deployed Worker uses
    assert.equal(r.status, 200); assert.ok(called.includes(conf.SubscribeURL));
    assert.deepEqual(db.subs.map((x) => [x.topic, x.ok]), [["permit", 1]]);
  } finally { globalThis.fetch = real; }
});
test("a confirmation call that fails outright is answered 502 and recorded as failed, with the reason", async () => {
  const conf = signed({ Type: "SubscriptionConfirmation", Token: "t", Message: "m", SubscribeURL: "https://sns.eu-west-2.amazonaws.com/?Action=ConfirmSubscription&Token=t" });
  const db = fakeDB(); const r = await handle(post("/permit", conf), env(db), deps({ fetch: async () => { throw new Error("network down"); } }));
  assert.equal(r.status, 502); assert.deepEqual(db.subs.map((x) => [x.topic, x.ok, x.note]), [["permit", 0, "confirmation call failed: network down"]]);
});
test("an unexpected failure after verification is recorded and answered 500, so Amazon tries again; unverified messages still write nothing", async () => {
  const db = fakeDB(), orig = db.prepare.bind(db);
  db.prepare = (sql) => /INSERT INTO msgs/i.test(sql) ? { bind() { return { async run() { throw new Error("d1 down"); } }; } } : orig(sql);
  const r = await handle(post("/permit", signed()), env(db), deps());
  assert.equal(r.status, 500); assert.deepEqual(db.subs.map((x) => [x.topic, x.ok, x.note]), [["permit", 0, "error: d1 down"]]);
  const m = signed(); m.Message = "tampered"; const n = db.subs.length;
  assert.equal((await handle(post("/permit", m), env(db), deps())).status, 403); assert.equal(db.subs.length, n);
});
