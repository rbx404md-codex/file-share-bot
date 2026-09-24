# RBX404 Digital File Platform V2

Telegram file-sharing bot + built-in Mini App + admin dashboard.
Upgraded from the original single-file `file share bot.py` — same core
ideas (folders, favorites, collections, expiry, recycle bin, backups),
rebuilt on SQLite + a real web layer so the Mini App / admin dashboard
could exist at all.

**No custom domain required.** Deploys on Railway's free/trial tier and
uses Railway's auto-generated HTTPS URL for everything (bot, Mini App,
share pages).

---

## 1. What changed vs. the old file

| | Old (`file share bot.py`) | New (V2) |
|---|---|---|
| Storage | one JSON file, rewritten whole on every change | SQLite (aiosqlite), indexed, async-safe |
| UI | Telegram inline keyboards only | Bot + real Telegram Mini App + admin dashboard |
| Force-join | per-file only | global multi-channel/group engine + per-file |
| Token | hardcoded fallback in source | env var only, no fallback |
| Structure | 1 file, 2,647 lines | modular `app/bot`, `app/web`, `miniapp/` |

⚠️ **Rotate your bot token in @BotFather before deploying this.** The old
file had a real token hardcoded as a fallback default — treat that token
as burned even though it's not reused anywhere here.

## 2. Project layout

```
rbx404/
├── app/
│   ├── config.py          # env vars, auto BASE_URL detection
│   ├── database.py        # SQLite schema + all queries
│   ├── migrate_json.py    # one-off: old database.json -> SQLite
│   ├── bot/                handlers, keyboards, bn/en texts
│   └── web/                 REST API, admin API, public share pages
├── miniapp/                 the Mini App itself (vanilla HTML/CSS/JS)
├── main.py                  runs the bot + web server together
├── requirements.txt
├── .env.example
├── Procfile / railway.toml
```

## 3. Deploy to Railway (no domain needed)

1. **Create the bot**: talk to [@BotFather](https://t.me/BotFather) →
   `/newbot` → copy the token.
2. **Get your Telegram user ID** (e.g. via [@userinfobot](https://t.me/userinfobot)).
3. **Create a private channel** for file storage, add your bot as admin
   with post/delete permissions, copy its numeric id (starts with `-100...`;
   forward any message from it to [@userinfobot](https://t.me/userinfobot) to read the id).
4. Push this folder to a GitHub repo.
5. On [railway.app](https://railway.app): New Project → Deploy from GitHub repo.
6. In the service's **Variables** tab, add (see `.env.example` for the full list):
   ```
   BOT_TOKEN=<from BotFather>
   ADMIN_IDS=<your numeric id>
   FILE_CHANNEL=<the -100... channel id>
   SIGNING_SECRET=<any long random string>
   ```
   Leave `BASE_URL` and `PORT` **blank** — Railway supplies `PORT` automatically
   and `main.py` reads `RAILWAY_PUBLIC_DOMAIN` for the public URL.
7. In **Settings → Networking**, click **Generate Domain** so Railway assigns
   a free `*.up.railway.app` HTTPS URL. This is what becomes your Mini App URL —
   no purchase needed.
8. Deploy. Check `https://<your-app>.up.railway.app/health` returns `{"status":"ok"}`.
9. Open your bot in Telegram and send `/start`.

### Registering the Mini App with BotFather (optional, for a menu-button launcher)
`/mybots` → your bot → **Bot Settings → Menu Button** → set the URL to
`https://<your-app>.up.railway.app/app`. (The in-chat "Open Mini App" button
built into `/start` works immediately without this step.)

### Bringing over old data
If you have an existing `database.json` from the old bot:
```
python -m app.migrate_json /path/to/old/database.json
```
Run this once, locally or via Railway's shell, **before** first real use —
it only inserts into the new SQLite file and never touches the source JSON.

## 4. Local development
```
cp .env.example .env      # fill in BOT_TOKEN, ADMIN_IDS, FILE_CHANNEL, SIGNING_SECRET
pip install -r requirements.txt
python main.py
```
Telegram will not open a Mini App button pointing at `http://localhost`.
For local Mini App testing, run a tunnel (`ngrok http 8080` or
`cloudflared tunnel --url http://localhost:8080`) and put its HTTPS URL in
`BASE_URL` in `.env`.

## 5. Feature list (implemented)
- Upload any file/video/photo/audio/voice/animation/sticker, or forward any
  message → instant secure share link (message-to-link generator)
- Per-file: expiry (1h/1d/7d/30d/never), download limit, one-time link,
  password field, disable/enable, per-file force-join channel
- Global force-join: multiple channels/groups, admin-managed, re-verify button
- Folders, Favorites, Collections (with public share pages), tags field
- Recycle bin: trash / restore / permanent delete / auto-purge after
  `TRASH_RETENTION_DAYS`
- QR code per file (bot button + Mini App + public share page)
- Duplicate-upload detection (name+size heuristic) with "Use Existing /
  Upload Anyway" choice
- Public branded share landing page at `/share/<token>` and `/collection/<id>`
- Mini App: home dashboard, file manager with search/type/folder filters,
  folder create + move (single-file and multi-select bulk move), favorites,
  collections, trash, profile, language switch (bn/en)
- Admin dashboard (Mini App): platform stats, user search/ban/unban,
  force-join management, broadcast with live sent/failed/blocked counts,
  audit log
- JSON backup/restore of the whole SQLite dataset (`Database.dump_all` /
  `restore_all` — wire up an `/backup` command or admin-API route if you
  want it triggered from the UI)
- `/health` endpoint, graceful startup validation, structured logging

## 6. Known limitations / not built (be upfront about these)
- **Duplicate-file detection** — implemented as a **name + size match**, not a
  true content hash. The Bot API doesn't expose raw bytes for large files, so
  a real hash would mean downloading every upload first; this heuristic
  catches the common "oops, sent this again" case without that cost.
- **Per-notification-type toggles** — there's a single `notify` on/off per
  user, not the full itemized list from the spec (download/expiry/etc each
  toggled separately).
- **Referral links / custom emoji** — not implemented; low value versus
  everything else, cut to keep the core solid.
- **Bulk multi-select** — ✅ done: tap ☑ on the Files page to select
  multiple files, then bulk-favorite / bulk-move-to-folder / bulk-trash from
  the bottom action bar.
- **PostgreSQL** — schema is SQLite-specific; migrating to Postgres later
  is possible but not wired up (spec allows SQLite-only, so this is by design).
- **Password-protected links** — now enforced: `deliver_file` prompts for the
  password in the bot chat before copying the file, and rejects a wrong one.
  This lives in an in-memory dict (`_pending_password`), so it only works
  within a single running process — fine for Railway's default one-instance
  setup, but won't survive a restart mid-prompt (the user just taps the link
  again) and won't work if you ever scale to multiple instances without a
  shared store (e.g. Redis) instead.

## 7. Testing checklist
- [ ] `/start` (fresh user) → welcome + Mini App button
- [ ] `/start` with force-join channels configured → verification screen → Verify
- [ ] Upload a document/video/photo → link + QR + settings button all work
- [ ] Upload the exact same file (same name+size) again → duplicate prompt appears → try both "Use Existing" and "Upload Anyway"
- [ ] Set a password on a file from the Mini App → open its `/start f_<token>` link → bot asks for password → wrong password rejected, correct one delivers the file
- [ ] Create a folder in the Mini App, move a file into it via the file modal's Folder dropdown, filter Files by that folder
- [ ] Enter Select mode (☑), select 2+ files, try Favorite / Move to Folder / Trash from the bulk bar
- [ ] Open Mini App → Home stats load, Files list loads, search/filter works
- [ ] Favorite / unfavorite a file
- [ ] Create a public collection, open its `/collection/<id>` page
- [ ] Trash a file → appears in Recycle Bin → Restore → back in Files
- [ ] Permanently delete a trashed file → gone from channel + DB
- [ ] `/share/<token>` public page loads and "Open in Telegram" resolves via `/start f_<token>`
- [ ] `/admin` (as an ADMIN_ID) → dashboard loads; a non-admin gets "Admins only"
  and the admin API returns 403
- [ ] Ban/unban a user from the admin Users tab
- [ ] Add/remove a force-join requirement from the admin panel
- [ ] Send a small broadcast, watch sent/failed/blocked update live
- [ ] `GET /health` returns 200 after a Railway restart
- [ ] Run `app/migrate_json.py` against a sample old `database.json` and
  confirm users/files show up in the Mini App

## 8. Security notes
- `BOT_TOKEN` has **no hardcoded fallback** anywhere in this codebase —
  the app refuses to start meaningfully without it in the environment.
- Every Mini App API request is authenticated by validating Telegram's
  `initData` HMAC signature server-side (`app/bot/utils.py:verify_webapp_init_data`)
  — the frontend never gets to just assert a user id.
- Admin routes re-check `ADMIN_IDS` server-side on every request; the
  frontend showing/hiding an admin link is cosmetic only, not a security boundary.
