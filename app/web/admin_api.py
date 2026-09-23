import asyncio
import uuid
from aiohttp import web
from app.config import config
from app.web.auth import require_admin
from app.bot.utils import fmt_size

routes = web.RouteTableDef()

_broadcast_jobs = {}  # job_id -> {"sent":0,"failed":0,"blocked":0,"total":0,"done":False}


@routes.get("/api/admin/stats")
@require_admin
async def stats(request):
    db = request.app["db"]
    s = await db.platform_stats()
    s["storage_h"] = fmt_size(s["storage_bytes"])
    return web.json_response(s)


@routes.get("/api/admin/users")
@require_admin
async def users(request):
    db = request.app["db"]
    q = request.query.get("q", "")
    page = int(request.query.get("page", 0))
    rows = await db.search_users(q, page=page) if q else \
        await db.search_users("", page=page, pp=20)
    return web.json_response({"users": rows})


@routes.post("/api/admin/users/{id}/ban")
@require_admin
async def ban_user(request):
    uid = int(request.match_info["id"])
    await request.app["db"].ban(uid)
    await request.app["db"].audit(request["uid"], "ban_user", str(uid))
    return web.json_response({"ok": True})


@routes.post("/api/admin/users/{id}/unban")
@require_admin
async def unban_user(request):
    uid = int(request.match_info["id"])
    await request.app["db"].unban(uid)
    await request.app["db"].audit(request["uid"], "unban_user", str(uid))
    return web.json_response({"ok": True})


@routes.get("/api/admin/force-join")
@require_admin
async def list_fj(request):
    return web.json_response({"channels": await request.app["db"].list_force_join()})


@routes.post("/api/admin/force-join")
@require_admin
async def add_fj(request):
    body = await request.json()
    chat_id = (body.get("chat_id") or "").strip()
    if not chat_id:
        return web.json_response({"error": "chat_id required"}, status=400)
    row_id = await request.app["db"].add_force_join(
        chat_id, body.get("title", chat_id), body.get("url", ""),
        body.get("kind", "channel"),
    )
    await request.app["db"].audit(request["uid"], "add_force_join", chat_id)
    return web.json_response({"id": row_id})


@routes.patch("/api/admin/force-join/{id}")
@require_admin
async def toggle_fj(request):
    body = await request.json()
    await request.app["db"].set_force_join_enabled(
        int(request.match_info["id"]), bool(body.get("enabled", True))
    )
    return web.json_response({"ok": True})


@routes.delete("/api/admin/force-join/{id}")
@require_admin
async def remove_fj(request):
    await request.app["db"].remove_force_join(int(request.match_info["id"]))
    await request.app["db"].audit(request["uid"], "remove_force_join", request.match_info["id"])
    return web.json_response({"ok": True})


@routes.get("/api/admin/audit-log")
@require_admin
async def audit_log(request):
    rows = await request.app["db"].audit_log(page=int(request.query.get("page", 0)))
    return web.json_response({"log": rows})


async def _run_broadcast(bot, db, job_id, uids, text):
    job = _broadcast_jobs[job_id]
    for uid in uids:
        try:
            await bot.send_message(uid, text)
            job["sent"] += 1
        except Exception as e:
            name = type(e).__name__
            if "Forbidden" in name or "blocked" in str(e).lower():
                job["blocked"] += 1
            else:
                job["failed"] += 1
        await asyncio.sleep(0.05)  # stay well under Telegram's rate limits
    job["done"] = True


@routes.post("/api/admin/broadcast")
@require_admin
async def broadcast(request):
    body = await request.json()
    text = (body.get("message") or "").strip()
    audience = body.get("audience", "all")
    if not text:
        return web.json_response({"error": "message required"}, status=400)
    db = request.app["db"]
    uids = await db.all_uids(active_only=(audience == "active"))
    job_id = uuid.uuid4().hex[:10]
    _broadcast_jobs[job_id] = {"sent": 0, "failed": 0, "blocked": 0,
                                "total": len(uids), "done": False}
    await db.audit(request["uid"], "broadcast", audience, text[:200])
    asyncio.create_task(_run_broadcast(request.app["bot"], db, job_id, uids, text))
    return web.json_response({"job_id": job_id, "total": len(uids)})


@routes.get("/api/admin/broadcast/{job_id}")
@require_admin
async def broadcast_status(request):
    job = _broadcast_jobs.get(request.match_info["job_id"])
    if not job:
        return web.json_response({"error": "not found"}, status=404)
    return web.json_response(job)


@routes.get("/api/admin/files")
@require_admin
async def admin_files(request):
    db = request.app["db"]
    q = request.query.get("q", "")
    # Reuses the per-user search across all users for moderation purposes.
    cur = await db._conn.execute(
        "SELECT * FROM files WHERE file_name LIKE ? AND deleted=0 ORDER BY created_at DESC LIMIT 50",
        (f"%{q}%",),
    )
    from app.database import row_to_dict
    rows = [row_to_dict(r) for r in await cur.fetchall()]
    return web.json_response({"files": rows})
