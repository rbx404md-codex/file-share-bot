import io
from aiohttp import web
from app.config import config
from app.bot.utils import fmt_size

routes = web.RouteTableDef()

PAGE_TMPL = """<!DOCTYPE html>
<html lang="bn"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — {brand}</title>
<style>
:root{{--bg:#0a0a0c;--card:#141417;--red:#e0223b;--text:#f2f2f4;--muted:#8a8a92;}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--text);font-family:-apple-system,Segoe UI,Roboto,sans-serif;
     min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px}}
.card{{background:var(--card);border:1px solid #232328;border-radius:20px;padding:32px 28px;max-width:380px;width:100%;
      box-shadow:0 20px 60px rgba(224,34,59,.08)}}
.brand{{font-weight:800;letter-spacing:2px;color:var(--red);font-size:13px;text-align:center;margin-bottom:4px}}
.sub{{color:var(--muted);font-size:11px;text-align:center;letter-spacing:3px;margin-bottom:24px}}
.fname{{font-size:18px;font-weight:600;word-break:break-word;margin-bottom:16px;text-align:center}}
.meta{{display:flex;justify-content:space-between;color:var(--muted);font-size:13px;padding:10px 0;border-top:1px solid #232328}}
.status{{color:#3ddc84}}
.btn{{display:block;text-align:center;background:var(--red);color:#fff;text-decoration:none;font-weight:700;
     padding:14px;border-radius:12px;margin-top:20px}}
.foot{{text-align:center;color:var(--muted);font-size:11px;margin-top:18px}}
.err{{color:var(--muted);text-align:center}}
</style></head><body>
<div class="card">
<div class="brand">{brand}</div>
<div class="sub">DIGITAL FILE SHARE</div>
{body}
</div></body></html>"""


def render(title, body):
    return PAGE_TMPL.format(title=title, brand=config.BRAND_NAME, body=body)


@routes.get("/share/{token}")
async def share_page(request):
    db = request.app["db"]
    token = request.match_info["token"]
    f = await db.get_file(token)
    if not f or f.get("disabled"):
        html = f'<div class="fname">😕</div><p class="err">File not found, disabled, or expired.</p>'
        return web.Response(text=render("Not found", html), content_type="text/html", status=404)

    await db.touch_view(token)
    limit_txt = "Unlimited" if not f["download_limit"] else f"{f['downloads']}/{f['download_limit']}"
    lock_note = (
        '<div class="meta"><span>🔒 Protected</span><span>password required in bot</span></div>'
        if f.get("password") else ""
    )
    body = f"""
    <div class="fname">📦 {f['file_name']}</div>
    <div class="meta"><span>Size</span><span>{fmt_size(f['size'])}</span></div>
    <div class="meta"><span>Downloads</span><span>{limit_txt}</span></div>
    <div class="meta"><span>Status</span><span class="status">🟢 Available</span></div>
    {lock_note}
    <a class="btn" href="https://t.me/{request.app['bot_username']}?start=f_{token}">OPEN IN TELEGRAM</a>
    <div class="foot">Secured by {config.BRAND_NAME}</div>
    """
    return web.Response(text=render(f['file_name'], body), content_type="text/html")


@routes.get("/collection/{cid}")
async def collection_page(request):
    db = request.app["db"]
    cid = request.match_info["cid"]
    col = await db.get_collection(cid)
    if not col or not col.get("is_public"):
        html = '<div class="fname">😕</div><p class="err">Collection not found or private.</p>'
        return web.Response(text=render("Not found", html), content_type="text/html", status=404)
    files = await db.collection_files(cid)
    body = f"""
    <div class="fname">📦 {col['name']}</div>
    <div class="meta"><span>Files</span><span>{len(files)}</span></div>
    <a class="btn" href="https://t.me/{request.app['bot_username']}?start=c_{cid}">OPEN IN TELEGRAM</a>
    <div class="foot">Secured by {config.BRAND_NAME}</div>
    """
    return web.Response(text=render(col['name'], body), content_type="text/html")


@routes.get("/share/{token}/qr.png")
async def share_qr(request):
    if not config.ENABLE_QR:
        return web.Response(status=404)
    import qrcode
    token = request.match_info["token"]
    img = qrcode.make(f"{config.BASE_URL}/share/{token}")
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return web.Response(body=buf.getvalue(), content_type="image/png")
