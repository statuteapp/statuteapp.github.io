// Street Manager receiver. Amazon SNS POSTs DfT's open-data notifications to /permit, /activity and /section58.
// Each message is verified (src/sns.js), then the Street Manager event inside it is queued in D1. An hourly GitHub job
// collects the queue with GET /drain and clears what it has processed with POST /ack (both need the DRAIN_TOKEN secret).
import { TOPICS, verifySns, subscribeUrlOk, fetchCertPem } from "./sns.js";

const json = (o, s = 200) => new Response(JSON.stringify(o), { status: s, headers: { "content-type": "application/json", "cache-control": "no-store" } });
const MAX_BODY = 262144;

function safeEqual(a, b) {
  if (a.length !== b.length) return false;
  let d = 0;
  for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return d === 0;
}
const authed = (req, env) => !!env.DRAIN_TOKEN && safeEqual(req.headers.get("authorization") || "", "Bearer " + env.DRAIN_TOKEN);

// Records what happened to a verified subscription message, or a failure after verification, so the owner can see it in the database.
// Never throws: logging must not stop the answer. Messages that fail verification are never recorded.
async function logSub(env, topic, ok, note) {
  try { await env.DB.prepare("INSERT INTO subs (topic, at, ok, note) VALUES (?1, ?2, ?3, ?4)").bind(topic, new Date().toISOString(), ok, String(note).slice(0, 200)).run(); } catch (e) { /* logging must never stop the answer */ }
}
const why = (e) => (e && e.message ? e.message : String(e));

async function receive(req, env, topic, deps) {
  const raw = await req.text();
  if (raw.length > MAX_BODY) return json({ error: "too large" }, 413);
  let m;
  try { m = JSON.parse(raw); } catch (e) { return json({ error: "bad json" }, 400); }
  if (!m || typeof m !== "object" || m.TopicArn !== TOPICS[topic]) return json({ error: "unknown topic" }, 403);
  const hdr = req.headers.get("x-amz-sns-message-type");
  if (hdr && hdr !== m.Type) return json({ error: "type mismatch" }, 400);
  if (!(await verifySns(m, deps.getCert))) return json({ error: "bad signature" }, 403);
  try {
    return await verified(m, env, topic, deps);
  } catch (e) {
    // Anything unexpected after verification is recorded and answered with a 5xx, so Amazon tries again.
    await logSub(env, topic, 0, "error: " + why(e));
    return json({ error: "internal error" }, 500);
  }
}

async function verified(m, env, topic, deps) {
  if (m.Type === "SubscriptionConfirmation") {
    if (!subscribeUrlOk(m.SubscribeURL)) return json({ error: "bad subscribe address" }, 400);
    let r;
    try { r = await deps.fetch(m.SubscribeURL); } catch (e) { await logSub(env, topic, 0, "confirmation call failed: " + why(e)); return json({ error: "confirmation call failed" }, 502); }
    // Keep a record that a verified confirmation arrived, so the owner can tell whether DfT has activated the address.
    await logSub(env, topic, r.ok ? 1 : 0, "status " + (r.status || ""));
    return json({ confirmed: r.ok }, r.ok ? 200 : 502);
  }
  if (m.Type === "Notification") {
    let inner;
    try { inner = JSON.parse(m.Message); } catch (e) { return json({ error: "bad message" }, 400); }
    if (!inner || typeof inner !== "object" || typeof inner.event_reference !== "number" || !inner.object_data) return json({ error: "not a street manager event" }, 400);
    await env.DB.prepare("INSERT INTO msgs (topic, at, body) VALUES (?1, ?2, ?3)").bind(topic, new Date().toISOString(), m.Message).run();
    return json({ stored: true });
  }
  if (m.Type === "UnsubscribeConfirmation") return json({ ok: true });
  return json({ error: "unsupported" }, 400);
}

async function drain(req, env, url) {
  if (!authed(req, env)) return json({ error: "unauthorised" }, 401);
  const after = Number(url.searchParams.get("after") || 0) || 0;
  const limit = Math.min(Math.max(Number(url.searchParams.get("limit") || 2000) || 2000, 1), 3000);
  const { results } = await env.DB.prepare("SELECT id, topic, at, body FROM msgs WHERE id > ?1 ORDER BY id LIMIT ?2").bind(after, limit).all();
  return json({ count: results.length, max_id: results.length ? results[results.length - 1].id : after, messages: results });
}

// Deletes processed rows but always keeps the newest one, so ids keep rising and a cursor is never reused.
async function ack(req, env, url) {
  if (!authed(req, env)) return json({ error: "unauthorised" }, 401);
  const upto = Number(url.searchParams.get("upto") || 0);
  if (!(upto > 0)) return json({ error: "upto required" }, 400);
  const r = await env.DB.prepare("DELETE FROM msgs WHERE id <= ?1 AND id < (SELECT MAX(id) FROM msgs)").bind(upto).run();
  return json({ deleted: r.meta.changes });
}

// fetch is wrapped, not handed over as it is: Cloudflare throws "Illegal invocation" if it is later called as deps.fetch(...).
export async function handle(req, env, deps = { getCert: fetchCertPem, fetch: (u) => fetch(u) }) {
  const url = new URL(req.url);
  const path = url.pathname.replace(/\/+$/, "") || "/";
  if (req.method === "POST" && (path === "/permit" || path === "/activity" || path === "/section58")) return receive(req, env, path.slice(1), deps);
  if (req.method === "GET" && path === "/drain") return drain(req, env, url);
  if (req.method === "POST" && path === "/ack") return ack(req, env, url);
  if (req.method === "GET" && path === "/health") return json({ ok: true });
  return json({ error: "not found" }, 404);
}

export default { fetch: (req, env) => handle(req, env) };
