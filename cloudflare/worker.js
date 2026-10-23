// The hosted chart. Static assets (web/index.html) are served at "/"; this
// Worker answers the two paths the page polls, from one Durable Object that
// live.py --publish fills over HTTP:
//   POST /push/<pk>              {"meta": {...}, "csv": "..."}  (Bearer PUSH_TOKEN)
//   GET  /runs/<pk>.csv          the latest CSV live.py wrote
//   GET  /runs/<pk>-meta.json    {"pk", "away", "home"}
import { DurableObject } from "cloudflare:workers";

const MAX_CSV = 512 * 1024;

export class Feed extends DurableObject {
  async put(pk, meta, csv) {
    await this.ctx.storage.put({ [`meta:${pk}`]: meta, [`csv:${pk}`]: csv });
  }

  async read(key) {
    return (await this.ctx.storage.get(key)) ?? null;
  }
}

function authorized(request, token) {
  if (!token) return false;
  const got = new TextEncoder().encode(request.headers.get("authorization") ?? "");
  const want = new TextEncoder().encode(`Bearer ${token}`);
  return got.byteLength === want.byteLength && crypto.subtle.timingSafeEqual(got, want);
}

function text(body, status, type = "text/plain; charset=utf-8") {
  return new Response(body, { status, headers: { "content-type": type, "cache-control": "no-store" } });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const feed = env.FEED.get(env.FEED.idFromName("feed"));

    const push = url.pathname.match(/^\/push\/(\d+)$/);
    if (push && request.method === "POST") {
      if (!authorized(request, env.PUSH_TOKEN)) return text("unauthorized\n", 401);
      let body;
      try {
        body = await request.json();
      } catch {
        return text("body must be JSON\n", 400);
      }
      const { meta, csv } = body ?? {};
      if (typeof csv !== "string" || csv.length > MAX_CSV || !meta
          || typeof meta.away !== "string" || typeof meta.home !== "string") {
        return text("need {meta: {away, home}, csv}\n", 400);
      }
      const pk = push[1];
      await feed.put(pk, JSON.stringify({ pk: Number(pk), away: meta.away, home: meta.home }), csv);
      return text("ok\n", 200);
    }

    const run = url.pathname.match(/^\/runs\/(\d+)(\.csv|-meta\.json)$/);
    if (run && request.method === "GET") {
      const json = run[2] === "-meta.json";
      const value = await feed.read(`${json ? "meta" : "csv"}:${run[1]}`);
      if (value === null) return text("nothing published yet\n", 404);
      return text(value, 200, json ? "application/json" : "text/csv; charset=utf-8");
    }

    return text("not found\n", 404);
  },
};
