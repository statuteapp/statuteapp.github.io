import test from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { createSign } from "node:crypto";
import { mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { handle } from "../src/index.js";
import { TOPICS, certUrlOk, subscribeUrlOk, spkiFromCertDer } from "../src/sns.js";

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

test("a correctly signed permit notification is stored (signature version 1)", async () => {
  const db = fakeDB(); const r = await handle(post("/permit", signed()), env(db), deps());
  assert.equal(r.status, 200); assert.equal(db.rows.length, 1);
  assert.equal(db.rows[0].topic, "permit"); assert.deepEqual(JSON.parse(db.rows[0].body), EVENT);
});
test("signature version 2 (SHA-256) is accepted", async () => {
  const db = fakeDB(); const r = await handle(post("/permit", signed({}, "2")), env(db), deps());
  assert.equal(r.status, 200); assert.equal(db.rows.length, 1);
});
test("a message altered after signing is rejected and not stored", async () => {
  const db = fakeDB(); const m = signed(); m.Message = JSON.stringify({ ...EVENT, event_reference: 1 });
  const r = await handle(post("/permit", m), env(db), deps());
  assert.equal(r.status, 403); assert.equal(db.rows.length, 0);
});
test("a message signed by someone else's key is rejected", async () => {
  const db = fakeDB(); const m = signed(); m.Signature = Buffer.from("x".repeat(256)).toString("base64");
  assert.equal((await handle(post("/permit", m), env(db), deps())).status, 403); assert.equal(db.rows.length, 0);
});
test("a topic that does not match the address it was sent to is rejected", async () => {
  const db = fakeDB();
  assert.equal((await handle(post("/permit", signed({ TopicArn: TOPICS.activity })), env(db), deps())).status, 403);
  assert.equal((await handle(post("/activity", signed({ TopicArn: TOPICS.activity })), env(db), deps())).status, 200);
  assert.equal((await handle(post("/section58", signed({ TopicArn: TOPICS.section58 })), env(db), deps())).status, 200);
  assert.deepEqual(db.rows.map((r) => r.topic), ["activity", "section58"]);
});
test("a forged topic (another account's) is rejected", async () => {
  const db = fakeDB(); const r = await handle(post("/permit", signed({ TopicArn: "arn:aws:sns:eu-west-2:999999999999:prod-permit-topic" })), env(db), deps());
  assert.equal(r.status, 403); assert.equal(db.rows.length, 0);
});
test("certificate addresses must be https amazonaws SNS .pem files", () => {
  assert.ok(certUrlOk(CERT_URL)); assert.ok(certUrlOk("https://sns.us-east-1.amazonaws.com/x/y.pem"));
  for (const u of ["http://sns.eu-west-2.amazonaws.com/a.pem", "https://evil.example/a.pem", "https://sns.eu-west-2.amazonaws.com.evil.example/a.pem", "https://sns.eu-west-2.amazonaws.com/a.txt", "https://user@sns.eu-west-2.amazonaws.com/a.pem", "https://sns.eu-west-2.amazonaws.com:8443/a.pem", "nonsense", undefined])
    assert.equal(certUrlOk(u), false, String(u));
});
test("a bad certificate address is rejected even if the signature would verify", async () => {
  const db = fakeDB(); const r = await handle(post("/permit", signed({ SigningCertURL: "https://evil.example/c.pem" })), env(db), deps());
  assert.equal(r.status, 403); assert.equal(db.rows.length, 0);
});
test("bad json, oversize bodies and wrong methods", async () => {
  const db = fakeDB();
  assert.equal((await handle(post("/permit", "not json"), env(db), deps())).status, 400);
  assert.equal((await handle(post("/permit", "x".repeat(300000)), env(db), deps())).status, 413);
  assert.equal((await handle(new Request("https://r.test/permit"), env(db), deps())).status, 404);
  assert.equal((await handle(post("/nothing", {}), env(db), deps())).status, 404);
});
test("a notification that is not a street manager event is rejected", async () => {
  const db = fakeDB();
  for (const Message of ["not json", JSON.stringify({ hello: 1 }), JSON.stringify({ event_reference: "12", object_data: {} })])
    assert.equal((await handle(post("/permit", signed({ Message })), env(db), deps())).status, 400);
  assert.equal(db.rows.length, 0);
});
test("subscription confirmation: confirmed only for a verified message with an Amazon address", async () => {
  let called = []; const d = deps({ fetch: async (u) => { called.push(u); return { ok: true }; } });
  const good = signed({ Type: "SubscriptionConfirmation", Token: "tok", Message: "You have chosen to subscribe", SubscribeURL: "https://sns.eu-west-2.amazonaws.com/?Action=ConfirmSubscription&Token=tok" });
  const r = await handle(post("/permit", good), env(fakeDB()), d);
  assert.equal(r.status, 200); assert.deepEqual(called, [good.SubscribeURL]);
  called = [];
  const evil = signed({ Type: "SubscriptionConfirmation", Token: "tok", Message: "m", SubscribeURL: "https://evil.example/confirm" });
  assert.equal((await handle(post("/permit", evil), env(fakeDB()), d)).status, 400); assert.deepEqual(called, []);
  const forged = signed({ Type: "SubscriptionConfirmation", Token: "tok", Message: "m", SubscribeURL: good.SubscribeURL }); forged.Token = "other";
  assert.equal((await handle(post("/permit", forged), env(fakeDB()), d)).status, 403); assert.deepEqual(called, []);
  assert.ok(subscribeUrlOk(good.SubscribeURL) && !subscribeUrlOk("http://sns.eu-west-2.amazonaws.com/"));
});
test("a verified confirmation is recorded, a failed one is recorded as failed, and messages are not affected", async () => {
  const conf = (topic) => signed({ TopicArn: TOPICS[topic], Type: "SubscriptionConfirmation", Token: "t", Message: "m", SubscribeURL: "https://sns.eu-west-2.amazonaws.com/?Action=ConfirmSubscription&Token=t" });
  const db = fakeDB();
  assert.equal((await handle(post("/activity", conf("activity")), env(db), deps())).status, 200);
  assert.equal((await handle(post("/permit", conf("permit")), env(db), deps({ fetch: async () => ({ ok: false, status: 500 }) }))).status, 502);
  assert.deepEqual(db.subs.map((x) => [x.topic, x.ok, x.note]), [["activity", 1, "status "], ["permit", 0, "status 500"]]); assert.equal(db.rows.length, 0);
  const broken = { prepare() { throw new Error("db down"); } };   // a logging failure must not stop the confirmation
  assert.equal((await handle(post("/permit", conf("permit")), { DB: broken, DRAIN_TOKEN: "x" }, deps())).status, 200);
  const bad = signed({ TopicArn: TOPICS.permit, Type: "SubscriptionConfirmation", Token: "t", Message: "m", SubscribeURL: "https://sns.eu-west-2.amazonaws.com/?x=1" }); bad.Token = "tampered";
  const before = db.subs.length; assert.equal((await handle(post("/permit", bad), env(db), deps())).status, 403); assert.equal(db.subs.length, before);   // unverified: nothing written
});
test("drain and ack need the token; ack keeps the newest row so ids never repeat", async () => {
  const db = fakeDB();
  for (let i = 0; i < 5; i++) await handle(post("/permit", signed({ MessageId: "id" + i, Message: JSON.stringify({ ...EVENT, event_reference: 165000001 + i }) })), env(db), deps());
  const get = (path, token) => handle(new Request("https://r.test" + path, { headers: token ? { authorization: "Bearer " + token } : {} }), env(db), deps());
  assert.equal((await get("/drain")).status, 401); assert.equal((await get("/drain", "wrong")).status, 401);
  assert.equal((await handle(new Request("https://r.test/drain", { headers: { authorization: "Bearer " } }), { DB: db }, deps())).status, 401);   // no secret configured
  let j = await (await get("/drain?limit=3", "secret-token")).json();
  assert.deepEqual(j.messages.map((x) => x.id), [1, 2, 3]); assert.equal(j.max_id, 3);
  j = await (await get("/drain?after=3&limit=3", "secret-token")).json(); assert.deepEqual(j.messages.map((x) => x.id), [4, 5]);
  const ackR = (q, token = "secret-token") => handle(new Request("https://r.test/ack" + q, { method: "POST", headers: { authorization: "Bearer " + token } }), env(db), deps());
  assert.equal((await ackR("?upto=3", "bad")).status, 401); assert.equal((await ackR("")).status, 400);
  assert.equal((await (await ackR("?upto=3")).json()).deleted, 3); assert.deepEqual(db.rows.map((r) => r.id), [4, 5]);
  assert.equal((await (await ackR("?upto=99")).json()).deleted, 1); assert.deepEqual(db.rows.map((r) => r.id), [5]);   // newest row stays
  await handle(post("/permit", signed({ MessageId: "later", Message: JSON.stringify({ ...EVENT, event_reference: 165000099 }) })), env(db), deps());
  assert.equal(db.rows.at(-1).id, 6);                                                                                // continues, never reuses
});
test("health check", async () => { const r = await handle(new Request("https://r.test/health"), env(fakeDB()), deps()); assert.equal(r.status, 200); assert.deepEqual(await r.json(), { ok: true }); });
test("the public key is found in a real certificate", () => {
  const der = Uint8Array.from(atob(CERT.replace(/-----[^-]+-----/g, "").replace(/\s+/g, "")), (c) => c.charCodeAt(0));
  const spki = spkiFromCertDer(der); assert.equal(spki[0], 0x30); assert.ok(spki.length > 250 && spki.length < 300);
});
