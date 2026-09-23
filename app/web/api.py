import io
import json
from aiohttp import web
from app.config import config
from app.web.auth import require_user
from app.bot.utils import fmt_size

routes = web.RouteTableDef()


def file_public(f, base_url):
    return {
        "id": f["id"], "name": f["file_name"], "type": f["file_type"],
        "size": f["size"], "size_h": fmt_size(f["size"]),
        "folder_id": f["folder_id"], "collection_id": f["collection_id"],
        "tags": f.get("tags") or [], "expiry_type": f["expiry_type"],
        "expires_at": f["expires_at"], "download_limit": f["download_limit"],
        "downloads": f["downloads"], "views": f["views"],
        "one_time": bool(f["one_time"]), "has_password": bool(f["password"]),
        "force_join": f["force_join"], "disabled": bool(f["disabled"]),
        "created_at": f["created_at"], "share_url": f"{base_url}/share/{f['id']}",
    }


@routes.get("/api/me")
@require_user
async def me(request):
    db = request.app["db"]
    uid = request["uid"]
    await db.add_user(uid, request["tg_user"].get("first_name", ""),
                       request["tg_user"].get("username", ""))
    u = await db.get_user(uid)
    stats = await db.user_stats(uid)
    return web.json_response({
        "id": uid, "name": u.get("name"), "lang": u.get("lang") or config.DEFAULT_LANGUAGE,
        "notify": bool(u.get("notify", 1)), "is_admin": uid in config.ADMIN_IDS,
        "stats": {**stats, "storage_h": fmt_size(stats["storage_bytes"])},
        "brand": {"name": config.BRAND_NAME, "title": config.BRAND_TITLE},
    })


@routes.post("/api/me/lang")
@require_user
async def set_lang(request):
    body = await request.json()
    lang = body.get("lang", "bn")
    if lang not in ("bn", "en"):
        return web.json_response({"error": "bad lang"}, status=400)
    await request.app["db"].set_lang(request["uid"], lang)
    return web.json_response({"ok": True})


@routes.get("/api/files")
@require_user
async def list_files(request):
    db = request.app["db"]
    q = request.query
    folder_id = q.get("folder_id", "__any__")
    if folder_id == "root":
        folder_id = None
    rows, total = await db.user_files(
        request["uid"], folder_id=folder_id, ftype=q.get("type") or None,
        tag=q.get("tag") or None, query=q.get("q") or None,
        page=int(q.get("page", 0)), pp=int(q.get("pp", 20)),
    )
    favs = {f["id"] for f in (await db.user_favorites(request["uid"], pp=1000))[0]}
    out = []
    for f in rows:
        d = file_public(f, config.BASE_URL)
        d["favorite"] = f["id"] in favs
        out.append(d)
    return web.json_response({"files": out, "total": total})


@routes.get("/api/files/{id}")
@require_user
async def get_file(request):
    db = request.app["db"]
    f = await db.get_file(request.match_info["id"], include_deleted=True)
    if not f or f["user_id"] != request["uid"]:
        return web.json_response({"error": "not found"}, status=404)
    d = file_public(f, config.BASE_URL)
    d["deleted"] = bool(f["deleted"])
    d["favorite"] = await db.is_favorite(request["uid"], f["id"])
    return web.json_response(d)


async def _own_file_or_404(request):
    db = request.app["db"]
    f = await db.get_file(request.match_info["id"], include_deleted=True)
    if not f or f["user_id"] != request["uid"]:
        return None
    return f


@routes.patch("/api/files/{id}")
@require_user
async def update_file(request):
    f = await _own_file_or_404(request)
    if not f:
        return web.json_response({"error": "not found"}, status=404)
    body = await request.json()
    allowed = {"file_name", "folder_id", "collection_id", "tags", "expiry_type",
               "expires_at", "download_limit", "one_time", "password", "force_join",
               "disabled"}
    fields = {k: v for k, v in body.items() if k in allowed}
    if "password" in fields and fields["password"] == "":
        fields["password"] = None
    if fields:
        await request.app["db"].update_file(f["id"], **fields)
    return web.json_response({"ok": True})


@routes.post("/api/files/{id}/trash")
@require_user
async def trash_file(request):
    f = await _own_file_or_404(request)
    if not f:
        return web.json_response({"error": "not found"}, status=404)
    await request.app["db"].trash_file(f["id"])
    await request.app["db"].log_activity(request["uid"], "trash", f["id"], f["file_name"])
    return web.json_response({"ok": True})


@routes.post("/api/files/{id}/restore")
@require_user
async def restore_file(request):
    f = await _own_file_or_404(request)
    if not f:
        return web.json_response({"error": "not found"}, status=404)
    await request.app["db"].restore_file(f["id"])
    return web.json_response({"ok": True})


@routes.delete("/api/files/{id}")
@require_user
async def delete_file_permanent(request):
    f = await _own_file_or_404(request)
    if not f:
        return web.json_response({"error": "not found"}, status=404)
    if not f["deleted"]:
        return web.json_response({"error": "must be trashed first"}, status=400)
    db = request.app["db"]
    bot = request.app["bot"]
    try:
        await bot.delete_message(config.FILE_CHANNEL, f["message_id"])
    except Exception:
        pass
    await db.delete_file_permanent(f["id"])
    return web.json_response({"ok": True})


@routes.post("/api/files/{id}/favorite")
@require_user
async def add_fav(request):
    f = await _own_file_or_404(request)
    if not f:
        return web.json_response({"error": "not found"}, status=404)
    await request.app["db"].add_favorite(request["uid"], f["id"])
    return web.json_response({"ok": True})


@routes.delete("/api/files/{id}/favorite")
@require_user
async def remove_fav(request):
    await request.app["db"].remove_favorite(request["uid"], request.match_info["id"])
    return web.json_response({"ok": True})


@routes.get("/api/favorites")
@require_user
async def favorites(request):
    db = request.app["db"]
    rows, total = await db.user_favorites(request["uid"],
                                           page=int(request.query.get("page", 0)))
    return web.json_response({
        "files": [{**file_public(f, config.BASE_URL), "favorite": True} for f in rows],
        "total": total,
    })


@routes.get("/api/trash")
@require_user
async def trash(request):
    db = request.app["db"]
    rows, total = await db.user_trash(request["uid"], page=int(request.query.get("page", 0)))
    return web.json_response({
        "files": [file_public(f, config.BASE_URL) for f in rows],
        "total": total, "retention_days": config.TRASH_RETENTION_DAYS,
    })


@routes.get("/api/folders")
@require_user
async def list_folders(request):
    db = request.app["db"]
    parent = request.query.get("parent_id", "__any__")
    if parent == "root":
        parent = None
    return web.json_response({"folders": await db.user_folders(request["uid"], parent)})


@routes.post("/api/folders")
@require_user
async def create_folder(request):
    body = await request.json()
    name = (body.get("name") or "").strip()[:60]
    if not name:
        return web.json_response({"error": "name required"}, status=400)
    fid = await request.app["db"].create_folder(request["uid"], name, body.get("parent_id"))
    return web.json_response({"id": fid})


@routes.patch("/api/folders/{id}")
@require_user
async def rename_folder(request):
    body = await request.json()
    await request.app["db"].rename_folder(request.match_info["id"], (body.get("name") or "").strip()[:60])
    return web.json_response({"ok": True})


@routes.delete("/api/folders/{id}")
@require_user
async def delete_folder(request):
    await request.app["db"].delete_folder(request.match_info["id"])
    return web.json_response({"ok": True})


@routes.get("/api/collections")
@require_user
async def list_collections(request):
    db = request.app["db"]
    cols = await db.user_collections(request["uid"])
    out = []
    for c in cols:
        files = await db.collection_files(c["id"])
        out.append({**c, "is_public": bool(c["is_public"]), "file_count": len(files),
                     "share_url": f"{config.BASE_URL}/collection/{c['id']}"})
    return web.json_response({"collections": out})


@routes.post("/api/collections")
@require_user
async def create_collection(request):
    body = await request.json()
    name = (body.get("name") or "").strip()[:60]
    if not name:
        return web.json_response({"error": "name required"}, status=400)
    cid = await request.app["db"].create_collection(request["uid"], name,
                                                      bool(body.get("is_public")))
    return web.json_response({"id": cid})


@routes.get("/api/collections/{id}/files")
@require_user
async def collection_files(request):
    db = request.app["db"]
    col = await db.get_collection(request.match_info["id"])
    if not col or col["user_id"] != request["uid"]:
        return web.json_response({"error": "not found"}, status=404)
    files = await db.collection_files(col["id"])
    return web.json_response({"collection": col,
                               "files": [file_public(f, config.BASE_URL) for f in files]})


@routes.post("/api/collections/{id}/files/{fid}")
@require_user
async def add_to_collection(request):
    db = request.app["db"]
    fid = request.match_info["fid"]
    fl = await db.get_file(fid, include_deleted=True)
    if not fl or fl["user_id"] != request["uid"]:
        return web.json_response({"error": "not found"}, status=404)
    await db.update_file(fid, collection_id=request.match_info["id"])
    return web.json_response({"ok": True})


@routes.delete("/api/collections/{id}")
@require_user
async def delete_collection(request):
    db = request.app["db"]
    col = await db.get_collection(request.match_info["id"])
    if not col or col["user_id"] != request["uid"]:
        return web.json_response({"error": "not found"}, status=404)
    await db.delete_collection(col["id"])
    return web.json_response({"ok": True})


@routes.get("/api/activity")
@require_user
async def activity(request):
    rows = await request.app["db"].user_activity(request["uid"])
    return web.json_response({"activity": rows})


@routes.get("/api/files/{id}/qr.png")
@require_user
async def file_qr(request):
    f = await _own_file_or_404(request)
    if not f:
        return web.json_response({"error": "not found"}, status=404)
    if not config.ENABLE_QR:
        return web.json_response({"error": "qr disabled"}, status=404)
    import qrcode
    img = qrcode.make(f"{config.BASE_URL}/share/{f['id']}")
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return web.Response(body=buf.getvalue(), content_type="image/png")
