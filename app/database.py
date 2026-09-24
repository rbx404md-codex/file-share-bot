"""
Async SQLite data layer for RBX404 Digital File Platform.

Replaces the old single-JSON-file "database" from file_share_bot.py.
Every write here is a real indexed SQL statement instead of a full-file
rewrite, and all access goes through aiosqlite so it never blocks the
event loop.
"""
import json
import random
import string
import time
import datetime
import aiosqlite

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT DEFAULT '',
    username TEXT DEFAULT '',
    lang TEXT DEFAULT '',
    join_date TEXT,
    files_count INTEGER DEFAULT 0,
    total_downloads INTEGER DEFAULT 0,
    notify INTEGER DEFAULT 1,
    def_privacy TEXT DEFAULT 'private',
    def_expiry TEXT DEFAULT 'never',
    def_folder TEXT,
    banned INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS folders (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    parent_id TEXT,
    created_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_folders_user ON folders(user_id);

CREATE TABLE IF NOT EXISTS collections (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    is_public INTEGER DEFAULT 0,
    created_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_collections_user ON collections(user_id);

CREATE TABLE IF NOT EXISTS files (
    id TEXT PRIMARY KEY,               -- share token
    user_id INTEGER NOT NULL,
    message_id INTEGER,
    file_name TEXT,
    file_type TEXT,
    size INTEGER DEFAULT 0,
    folder_id TEXT,
    collection_id TEXT,
    tags TEXT DEFAULT '[]',            -- JSON list
    caption TEXT,
    expiry_type TEXT DEFAULT 'never',
    expires_at TEXT,
    download_limit INTEGER DEFAULT 0,  -- 0 = unlimited
    downloads INTEGER DEFAULT 0,
    views INTEGER DEFAULT 0,
    one_time INTEGER DEFAULT 0,
    password TEXT,
    force_join TEXT,                   -- optional single @channel for this file
    disabled INTEGER DEFAULT 0,
    deleted INTEGER DEFAULT 0,
    deleted_at TEXT,
    expiry_notified INTEGER DEFAULT 0,
    last_accessed TEXT,
    created_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_files_user ON files(user_id);
CREATE INDEX IF NOT EXISTS idx_files_folder ON files(folder_id);
CREATE INDEX IF NOT EXISTS idx_files_collection ON files(collection_id);
CREATE INDEX IF NOT EXISTS idx_files_deleted ON files(deleted);
CREATE INDEX IF NOT EXISTS idx_files_name ON files(file_name);

CREATE TABLE IF NOT EXISTS favorites (
    user_id INTEGER NOT NULL,
    file_id TEXT NOT NULL,
    created_at TEXT,
    PRIMARY KEY (user_id, file_id)
);

CREATE TABLE IF NOT EXISTS force_join_channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id TEXT NOT NULL,
    title TEXT,
    url TEXT,
    kind TEXT DEFAULT 'channel',   -- channel | group
    enabled INTEGER DEFAULT 1,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id INTEGER,
    action TEXT,
    target TEXT,
    detail TEXT,
    created_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at);

CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    kind TEXT,
    file_id TEXT,
    label TEXT,
    created_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_activity_user ON activity_log(user_id);

CREATE TABLE IF NOT EXISTS banned (
    user_id INTEGER PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""


def gen_id(n=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=n))


def now_iso():
    return datetime.datetime.utcnow().isoformat()


def row_to_dict(row):
    if row is None:
        return None
    d = dict(row)
    if "tags" in d and isinstance(d["tags"], str):
        try:
            d["tags"] = json.loads(d["tags"])
        except Exception:
            d["tags"] = []
    return d


class Database:
    def __init__(self, path):
        self.path = path
        self._conn: aiosqlite.Connection | None = None

    async def connect(self):
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript(SCHEMA)
        await self._conn.commit()

    async def close(self):
        if self._conn:
            await self._conn.close()

    # ── users ──────────────────────────────────────────────
    async def add_user(self, uid, name="", username=""):
        cur = await self._conn.execute("SELECT id FROM users WHERE id=?", (uid,))
        row = await cur.fetchone()
        if row:
            await self._conn.execute(
                "UPDATE users SET name=?, username=? WHERE id=?", (name, username, uid)
            )
            await self._conn.commit()
            return False
        await self._conn.execute(
            "INSERT INTO users (id,name,username,join_date) VALUES (?,?,?,?)",
            (uid, name, username, now_iso()),
        )
        await self._conn.commit()
        return True

    async def get_user(self, uid):
        cur = await self._conn.execute("SELECT * FROM users WHERE id=?", (uid,))
        return row_to_dict(await cur.fetchone())

    async def set_lang(self, uid, lang):
        await self._conn.execute("UPDATE users SET lang=? WHERE id=?", (lang, uid))
        await self._conn.commit()

    async def user_count(self):
        cur = await self._conn.execute("SELECT COUNT(*) c FROM users")
        return (await cur.fetchone())["c"]

    async def today_users(self):
        td = datetime.datetime.utcnow().strftime("%Y-%m-%d")
        cur = await self._conn.execute(
            "SELECT COUNT(*) c FROM users WHERE join_date LIKE ?", (td + "%",)
        )
        return (await cur.fetchone())["c"]

    async def all_uids(self, active_only=False):
        cur = await self._conn.execute(
            "SELECT id FROM users" + (" WHERE banned=0" if active_only else "")
        )
        return [r["id"] for r in await cur.fetchall()]

    async def inc_files(self, uid):
        await self._conn.execute(
            "UPDATE users SET files_count=files_count+1 WHERE id=?", (uid,)
        )
        await self._conn.commit()

    async def inc_dl(self, uid):
        await self._conn.execute(
            "UPDATE users SET total_downloads=total_downloads+1 WHERE id=?", (uid,)
        )
        await self._conn.commit()

    async def ban(self, uid):
        await self._conn.execute("UPDATE users SET banned=1 WHERE id=?", (uid,))
        await self._conn.commit()

    async def unban(self, uid):
        await self._conn.execute("UPDATE users SET banned=0 WHERE id=?", (uid,))
        await self._conn.commit()

    async def is_banned(self, uid):
        cur = await self._conn.execute("SELECT banned FROM users WHERE id=?", (uid,))
        r = await cur.fetchone()
        return bool(r and r["banned"])

    async def search_users(self, query, page=0, pp=20):
        like = f"%{query}%"
        cur = await self._conn.execute(
            "SELECT * FROM users WHERE name LIKE ? OR username LIKE ? OR CAST(id AS TEXT) LIKE ? "
            "ORDER BY join_date DESC LIMIT ? OFFSET ?",
            (like, like, like, pp, page * pp),
        )
        return [row_to_dict(r) for r in await cur.fetchall()]

    # ── files ──────────────────────────────────────────────
    async def add_file(self, uid, message_id, file_name, file_type, size,
                        folder_id=None, caption=None, expiry_type="never",
                        expires_at=None, download_limit=0, one_time=False,
                        tags=None):
        fid = gen_id()
        await self._conn.execute(
            "INSERT INTO files (id,user_id,message_id,file_name,file_type,size,folder_id,"
            "caption,expiry_type,expires_at,download_limit,one_time,tags,created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (fid, uid, message_id, file_name, file_type, size, folder_id, caption,
             expiry_type, expires_at, download_limit, int(one_time),
             json.dumps(tags or []), now_iso()),
        )
        await self._conn.commit()
        await self.inc_files(uid)
        return fid

    async def get_file(self, fid, include_deleted=False):
        cur = await self._conn.execute("SELECT * FROM files WHERE id=?", (fid,))
        f = row_to_dict(await cur.fetchone())
        if f and not include_deleted and f["deleted"]:
            return None
        return f

    async def find_duplicate(self, uid, file_name, size):
        """
        Lightweight duplicate signal: same owner, same name + size, not deleted.
        Not a content hash — the Bot API doesn't expose raw bytes for large
        files, so this is a practical (not perfect) heuristic. Good enough to
        catch "oops I sent this already" re-uploads.
        """
        cur = await self._conn.execute(
            "SELECT * FROM files WHERE user_id=? AND file_name=? AND size=? AND deleted=0 "
            "ORDER BY created_at DESC LIMIT 1",
            (uid, file_name, size),
        )
        return row_to_dict(await cur.fetchone())


    async def touch_view(self, fid):
        await self._conn.execute(
            "UPDATE files SET views=views+1, last_accessed=? WHERE id=?", (now_iso(), fid)
        )
        await self._conn.commit()

    async def touch_download(self, fid):
        await self._conn.execute(
            "UPDATE files SET downloads=downloads+1, last_accessed=? WHERE id=?",
            (now_iso(), fid),
        )
        await self._conn.commit()

    async def update_file(self, fid, **fields):
        if not fields:
            return
        if "tags" in fields and not isinstance(fields["tags"], str):
            fields["tags"] = json.dumps(fields["tags"])
        cols = ", ".join(f"{k}=?" for k in fields)
        await self._conn.execute(
            f"UPDATE files SET {cols} WHERE id=?", (*fields.values(), fid)
        )
        await self._conn.commit()

    async def trash_file(self, fid):
        await self._conn.execute(
            "UPDATE files SET deleted=1, deleted_at=? WHERE id=?", (now_iso(), fid)
        )
        await self._conn.commit()

    async def restore_file(self, fid):
        await self._conn.execute(
            "UPDATE files SET deleted=0, deleted_at=NULL WHERE id=?", (fid,)
        )
        await self._conn.commit()

    async def delete_file_permanent(self, fid):
        await self._conn.execute("DELETE FROM files WHERE id=?", (fid,))
        await self._conn.execute("DELETE FROM favorites WHERE file_id=?", (fid,))
        await self._conn.commit()

    async def user_files(self, uid, folder_id="__any__", ftype=None, tag=None,
                          query=None, page=0, pp=12):
        clauses = ["user_id=?", "deleted=0"]
        params = [uid]
        if folder_id != "__any__":
            clauses.append("folder_id IS ?" if folder_id is None else "folder_id=?")
            params.append(folder_id)
        if ftype:
            clauses.append("file_type=?")
            params.append(ftype)
        if tag:
            clauses.append("tags LIKE ?")
            params.append(f'%"{tag}"%')
        if query:
            clauses.append("file_name LIKE ?")
            params.append(f"%{query}%")
        where = " AND ".join(clauses)
        cur = await self._conn.execute(
            f"SELECT COUNT(*) c FROM files WHERE {where}", params
        )
        total = (await cur.fetchone())["c"]
        cur = await self._conn.execute(
            f"SELECT * FROM files WHERE {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (*params, pp, page * pp),
        )
        rows = [row_to_dict(r) for r in await cur.fetchall()]
        return rows, total

    async def user_trash(self, uid, page=0, pp=12):
        cur = await self._conn.execute(
            "SELECT COUNT(*) c FROM files WHERE user_id=? AND deleted=1", (uid,)
        )
        total = (await cur.fetchone())["c"]
        cur = await self._conn.execute(
            "SELECT * FROM files WHERE user_id=? AND deleted=1 ORDER BY deleted_at DESC "
            "LIMIT ? OFFSET ?",
            (uid, pp, page * pp),
        )
        return [row_to_dict(r) for r in await cur.fetchall()], total

    async def purge_old_trash(self, days=7):
        cutoff = (datetime.datetime.utcnow() - datetime.timedelta(days=days)).isoformat()
        cur = await self._conn.execute(
            "SELECT * FROM files WHERE deleted=1 AND deleted_at<?", (cutoff,)
        )
        rows = [row_to_dict(r) for r in await cur.fetchall()]
        if rows:
            ids = [r["id"] for r in rows]
            qs = ",".join("?" * len(ids))
            await self._conn.execute(f"DELETE FROM files WHERE id IN ({qs})", ids)
            await self._conn.commit()
        return rows

    async def expired_file_ids(self):
        now = now_iso()
        cur = await self._conn.execute(
            "SELECT id FROM files WHERE deleted=0 AND expiry_type!='never' "
            "AND expires_at IS NOT NULL AND expires_at<?",
            (now,),
        )
        return [r["id"] for r in await cur.fetchall()]

    async def soon_expiring(self, window_seconds=3600):
        now = datetime.datetime.utcnow()
        window = (now + datetime.timedelta(seconds=window_seconds)).isoformat()
        cur = await self._conn.execute(
            "SELECT * FROM files WHERE deleted=0 AND expiry_notified=0 AND "
            "expiry_type!='never' AND expires_at IS NOT NULL AND expires_at<? AND expires_at>?",
            (window, now.isoformat()),
        )
        return [row_to_dict(r) for r in await cur.fetchall()]

    async def mark_expiry_notified(self, fid):
        await self._conn.execute(
            "UPDATE files SET expiry_notified=1 WHERE id=?", (fid,)
        )
        await self._conn.commit()

    async def del_file(self, fid):
        await self.delete_file_permanent(fid)

    # ── folders ────────────────────────────────────────────
    async def create_folder(self, uid, name, parent_id=None):
        fid = gen_id(8)
        await self._conn.execute(
            "INSERT INTO folders (id,user_id,name,parent_id,created_at) VALUES (?,?,?,?,?)",
            (fid, uid, name, parent_id, now_iso()),
        )
        await self._conn.commit()
        return fid

    async def user_folders(self, uid, parent_id="__any__"):
        if parent_id == "__any__":
            cur = await self._conn.execute(
                "SELECT * FROM folders WHERE user_id=? ORDER BY name", (uid,)
            )
        else:
            cur = await self._conn.execute(
                "SELECT * FROM folders WHERE user_id=? AND parent_id IS ? ORDER BY name",
                (uid, parent_id),
            )
        return [row_to_dict(r) for r in await cur.fetchall()]

    async def rename_folder(self, fid, name):
        await self._conn.execute("UPDATE folders SET name=? WHERE id=?", (name, fid))
        await self._conn.commit()

    async def delete_folder(self, fid):
        await self._conn.execute(
            "UPDATE files SET folder_id=NULL WHERE folder_id=?", (fid,)
        )
        await self._conn.execute("DELETE FROM folders WHERE id=?", (fid,))
        await self._conn.commit()

    # ── favorites ──────────────────────────────────────────
    async def add_favorite(self, uid, fid):
        await self._conn.execute(
            "INSERT OR IGNORE INTO favorites (user_id,file_id,created_at) VALUES (?,?,?)",
            (uid, fid, now_iso()),
        )
        await self._conn.commit()

    async def remove_favorite(self, uid, fid):
        await self._conn.execute(
            "DELETE FROM favorites WHERE user_id=? AND file_id=?", (uid, fid)
        )
        await self._conn.commit()

    async def is_favorite(self, uid, fid):
        cur = await self._conn.execute(
            "SELECT 1 FROM favorites WHERE user_id=? AND file_id=?", (uid, fid)
        )
        return (await cur.fetchone()) is not None

    async def user_favorites(self, uid, page=0, pp=12):
        cur = await self._conn.execute(
            "SELECT COUNT(*) c FROM favorites WHERE user_id=?", (uid,)
        )
        total = (await cur.fetchone())["c"]
        cur = await self._conn.execute(
            "SELECT f.* FROM files f JOIN favorites fav ON f.id=fav.file_id "
            "WHERE fav.user_id=? AND f.deleted=0 ORDER BY fav.created_at DESC LIMIT ? OFFSET ?",
            (uid, pp, page * pp),
        )
        return [row_to_dict(r) for r in await cur.fetchall()], total

    # ── collections ────────────────────────────────────────
    async def create_collection(self, uid, name, is_public=False):
        cid = gen_id(8)
        await self._conn.execute(
            "INSERT INTO collections (id,user_id,name,is_public,created_at) VALUES (?,?,?,?,?)",
            (cid, uid, name, int(is_public), now_iso()),
        )
        await self._conn.commit()
        return cid

    async def get_collection(self, cid):
        cur = await self._conn.execute("SELECT * FROM collections WHERE id=?", (cid,))
        return row_to_dict(await cur.fetchone())

    async def user_collections(self, uid):
        cur = await self._conn.execute(
            "SELECT * FROM collections WHERE user_id=? ORDER BY created_at DESC", (uid,)
        )
        return [row_to_dict(r) for r in await cur.fetchall()]

    async def collection_files(self, cid):
        cur = await self._conn.execute(
            "SELECT * FROM files WHERE collection_id=? AND deleted=0 ORDER BY created_at", (cid,)
        )
        return [row_to_dict(r) for r in await cur.fetchall()]

    async def delete_collection(self, cid):
        await self._conn.execute(
            "UPDATE files SET collection_id=NULL WHERE collection_id=?", (cid,)
        )
        await self._conn.execute("DELETE FROM collections WHERE id=?", (cid,))
        await self._conn.commit()

    # ── force-join (global) ───────────────────────────────
    async def list_force_join(self, enabled_only=False):
        q = "SELECT * FROM force_join_channels"
        if enabled_only:
            q += " WHERE enabled=1"
        cur = await self._conn.execute(q + " ORDER BY id")
        return [row_to_dict(r) for r in await cur.fetchall()]

    async def add_force_join(self, chat_id, title, url, kind="channel"):
        cur = await self._conn.execute(
            "INSERT INTO force_join_channels (chat_id,title,url,kind,created_at) "
            "VALUES (?,?,?,?,?)",
            (str(chat_id), title, url, kind, now_iso()),
        )
        await self._conn.commit()
        return cur.lastrowid

    async def set_force_join_enabled(self, row_id, enabled):
        await self._conn.execute(
            "UPDATE force_join_channels SET enabled=? WHERE id=?", (int(enabled), row_id)
        )
        await self._conn.commit()

    async def remove_force_join(self, row_id):
        await self._conn.execute("DELETE FROM force_join_channels WHERE id=?", (row_id,))
        await self._conn.commit()

    # ── activity / audit ───────────────────────────────────
    async def log_activity(self, uid, kind, fid=None, label=""):
        await self._conn.execute(
            "INSERT INTO activity_log (user_id,kind,file_id,label,created_at) VALUES (?,?,?,?,?)",
            (uid, kind, fid, label, now_iso()),
        )
        await self._conn.commit()
        await self._conn.execute(
            "DELETE FROM activity_log WHERE id NOT IN ("
            "SELECT id FROM activity_log WHERE user_id=? ORDER BY id DESC LIMIT 20) AND user_id=?",
            (uid, uid),
        )
        await self._conn.commit()

    async def user_activity(self, uid, limit=20):
        cur = await self._conn.execute(
            "SELECT * FROM activity_log WHERE user_id=? ORDER BY id DESC LIMIT ?",
            (uid, limit),
        )
        return [row_to_dict(r) for r in await cur.fetchall()]

    async def audit(self, admin_id, action, target="", detail=""):
        await self._conn.execute(
            "INSERT INTO audit_log (admin_id,action,target,detail,created_at) VALUES (?,?,?,?,?)",
            (admin_id, action, target, detail, now_iso()),
        )
        await self._conn.commit()

    async def audit_log(self, page=0, pp=30):
        cur = await self._conn.execute(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT ? OFFSET ?", (pp, page * pp)
        )
        return [row_to_dict(r) for r in await cur.fetchall()]

    # ── stats ──────────────────────────────────────────────
    async def platform_stats(self):
        async def count(q, *p):
            cur = await self._conn.execute(q, p)
            return (await cur.fetchone())["c"]

        return {
            "users": await count("SELECT COUNT(*) c FROM users"),
            "banned": await count("SELECT COUNT(*) c FROM users WHERE banned=1"),
            "today_users": await self.today_users(),
            "files": await count("SELECT COUNT(*) c FROM files WHERE deleted=0"),
            "trashed": await count("SELECT COUNT(*) c FROM files WHERE deleted=1"),
            "downloads": (await self._conn.execute_fetchall(
                "SELECT COALESCE(SUM(downloads),0) c FROM files"))[0][0],
            "storage_bytes": (await self._conn.execute_fetchall(
                "SELECT COALESCE(SUM(size),0) c FROM files WHERE deleted=0"))[0][0],
        }

    async def user_stats(self, uid):
        cur = await self._conn.execute(
            "SELECT COUNT(*) c, COALESCE(SUM(size),0) s, COALESCE(SUM(downloads),0) d, "
            "COALESCE(SUM(views),0) v FROM files WHERE user_id=? AND deleted=0", (uid,)
        )
        row = await cur.fetchone()
        cur2 = await self._conn.execute(
            "SELECT COUNT(*) c FROM favorites WHERE user_id=?", (uid,)
        )
        fav = (await cur2.fetchone())["c"]
        return {
            "files": row["c"], "storage_bytes": row["s"], "downloads": row["d"],
            "views": row["v"], "favorites": fav,
        }

    # ── backup / restore ───────────────────────────────────
    async def dump_all(self):
        tables = ["users", "folders", "collections", "files", "favorites",
                  "force_join_channels", "settings"]
        out = {"signature": "RBX404_V2", "date": now_iso(), "tables": {}}
        for tname in tables:
            cur = await self._conn.execute(f"SELECT * FROM {tname}")
            out["tables"][tname] = [dict(r) for r in await cur.fetchall()]
        return out

    async def restore_all(self, dump):
        if dump.get("signature") not in ("RBX404_V2", "FILEBRO_V3"):
            raise ValueError("Unrecognized backup signature")
        tables = dump.get("tables", {})
        for tname, rows in tables.items():
            if not rows:
                continue
            cols = list(rows[0].keys())
            placeholders = ",".join("?" * len(cols))
            colnames = ",".join(cols)
            await self._conn.execute(f"DELETE FROM {tname}")
            for r in rows:
                await self._conn.execute(
                    f"INSERT INTO {tname} ({colnames}) VALUES ({placeholders})",
                    [r[c] for c in cols],
                )
        await self._conn.commit()
