// Only the permit events the owner chose are saved (6 October 2026), to stay within Cloudflare's free write limit.
// Skipped events are still answered 200, so Amazon does not keep resending them. Same helpers as receiver.test.mjs.
import test from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { createSign } from "node:crypto";
import { mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { handle, kept, KEEP_PERMIT_EVENTS } from "../src/index.js";
import { TOPICS } from "../src/sns.js";

const dir = mkdtempSync(join(tmpdir(), "sns-"));
execFileSync("openssl", ["req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", join(dir, "k.pem"), "-out", join(dir, "c.pem"), "-subj", "/CN=sns.test", "-days", "2"], { stdio: "ignore" });
const KEY = readFileSync(join(dir, "k.pem"), "utf8"), CERT = readFileSync(join(dir, "c.pem"), "utf8");
const CERT_URL = "https://sns.eu-west-2.amazonaws.com/SimpleNotificationService-test.pem";
const deps = { getCert: async () => CERT, fetch: async () => ({ ok: true }) };

function signed(topic, event_type) {
  const ev = { event_reference: 165000001, event_type, object_type: "PERMIT", object_reference: "W1-01", event_time: "2026-10-06T10:00:00.000Z", object_data: { work_reference_number: "W1" } };
  const m = { Type: "Notification", MessageId: "11111111-2222-3333-4444-555555555555", TopicArn: TOPICS[topic], Message: JSON.stringify(ev), Timestamp: "2026-10-06T10:00:01.000Z", SignatureVersion: "1", SigningCertURL: CERT_URL };
  const s = `Message\n${m.Message}\nMessageId\n${m.MessageId}\nTimestamp\n${m.Timestamp}\nTopicArn\n${m.TopicArn}\nType\n${m.Type}\n`;
  m.Signature = createSign("RSA-SHA1").update(s).sign(KEY, "base64");
  return m;
}
function fakeDB() {
  const rows = [];
  return { rows, prepare() { return { bind(...a) { return { async run() { rows.push(a); return { meta: { changes: 1 } }; } }; } }; } };
}
const post = (path, body) => new Request("https://r.test" + path, { method: "POST", body: JSON.stringify(body) });
const env = (db) => ({ DB: db, DRAIN_TOKEN: "t" });

const KEEP = ["PERMIT_GRANTED", "PERMIT_ALTERATION_GRANTED", "WORK_START", "WORK_STOP", "WORK_START_REVERTED", "WORK_STOP_REVERTED", "PERMIT_CANCELLED", "PERMIT_REVOKED", "CURRENT_TRAFFIC_MANAGEMENT_UPDATED"];
const SKIP = ["PERMIT_SUBMITTED", "PERMIT_REFUSED"];

test("the kept list is exactly the owner's nine permit events (seven chosen, plus the two corrections)", () => {
  assert.deepEqual([...KEEP_PERMIT_EVENTS].sort(), [...KEEP].sort());
});

for (const et of KEEP) test(`permit ${et} is saved`, async () => {
  const db = fakeDB(); const r = await handle(post("/permit", signed("permit", et)), env(db), deps);
  assert.equal(r.status, 200); assert.equal((await r.json()).stored, true); assert.equal(db.rows.length, 1);
});

for (const et of SKIP) test(`permit ${et} is answered 200 but not saved`, async () => {
  const db = fakeDB(); const r = await handle(post("/permit", signed("permit", et)), env(db), deps);
  assert.equal(r.status, 200); assert.equal((await r.json()).stored, false); assert.equal(db.rows.length, 0);
});

test("DfT's other spelling of event types is understood (work-start, permit-submitted)", () => {
  assert.equal(kept("permit", { event_type: "work-start" }), true);
  assert.equal(kept("permit", { event_type: "permit-submitted" }), false);
});

test("activities and Section 58 notices are all kept, whatever their event type", async () => {
  for (const [topic, et] of [["activity", "ACTIVITY_CREATED"], ["activity", "ACTIVITY_CANCELLED"], ["section58", "SECTION_58_CLOSED"]]) {
    const db = fakeDB(); const r = await handle(post("/" + topic, signed(topic, et)), env(db), deps);
    assert.equal(r.status, 200); assert.equal(db.rows.length, 1, topic + " " + et);
  }
});
