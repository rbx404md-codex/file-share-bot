"""
One-time migration: old file_share_bot.py `database.json` -> new SQLite DB.

Usage:
    python -m app.migrate_json path/to/old/database.json

Safe to run against a fresh SQLite file — it only INSERTs. It does not
touch or delete the source database.json. Run this ONCE before the first
deploy if you're carrying over existing users/files; skip it entirely for
a clean start.
"""
import asyncio
import json
import sys
from pathlib import Path

from app.config import config
from app.database import Database, now_iso


async def migrate(json_path: str):
    src = Path(json_path)
    if not src.exists():
        print(f"✗ Not found: {src}")
        return

    with open(src, "r", encoding="utf-8") as f:
        old = json.load(f)

    db = Database(config.DATABASE_PATH)
    await db.connect()

    users = old.get("users", {})
    folders = old.get("folders", {})
    collections = old.get("collections", {})
    files = old.get("files", {})
    favorites = old.get("favorites", {})
    banned = old.get("banned", [])

    print(f"Migrating {len(users)} users, {len(folders)} folders, "
          f"{len(collections)} collections, {len(files)} files ...")

    for uid, u in users.items():
        await db._conn.execute(
            "INSERT OR IGNORE INTO users (id,name,lang,join_date,files_count,"
            "total_downloads,notify,def_privacy,def_expiry,def_folder,banned) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (int(uid), u.get("name", ""), u.get("lang", ""), u.get("join_date", now_iso()),
             u.get("files_count", 0), u.get("total_downloads", 0),
             int(bool(u.get("notify", True))), u.get("def_privacy", "private"),
             u.get("def_expiry", "never"), u.get("def_folder"),
             int(int(uid) in banned)),
        )

    for fid, fo in folders.items():
        await db._conn.execute(
            "INSERT OR IGNORE INTO folders (id,user_id,name,parent_id,created_at) "
            "VALUES (?,?,?,?,?)",
            (fid, fo.get("user_id"), fo.get("name", "Untitled"),
             fo.get("parent_id"), fo.get("created", now_iso())),
        )

    for cid, co in collections.items():
        await db._conn.execute(
            "INSERT OR IGNORE INTO collections (id,user_id,name,is_public,created_at) "
            "VALUES (?,?,?,?,?)",
            (cid, co.get("user_id"), co.get("name", "Untitled"),
             int(bool(co.get("public", False))), co.get("created", now_iso())),
        )

    for fid, fl in files.items():
        await db._conn.execute(
            "INSERT OR IGNORE INTO files (id,user_id,message_id,file_name,file_type,size,"
            "folder_id,collection_id,tags,caption,expiry_type,expires_at,download_limit,"
            "downloads,views,one_time,password,force_join,disabled,deleted,deleted_at,"
            "expiry_notified,last_accessed,created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (fid, fl.get("user_id"), fl.get("message_id"), fl.get("file_name", "Untitled"),
             fl.get("file_type", "document"), fl.get("size", 0), fl.get("folder_id"),
             fl.get("collection_id"), json.dumps(fl.get("tags", [])), fl.get("caption"),
             fl.get("expiry_type", "never"), fl.get("expires_at"),
             fl.get("download_limit", 0), fl.get("downloads", 0), fl.get("views", 0),
             int(bool(fl.get("one_time", False))), fl.get("password"),
             fl.get("force_join"), int(bool(fl.get("disabled", False))),
             int(bool(fl.get("deleted", False))), fl.get("deleted_at"),
             int(bool(fl.get("expiry_notified", False))), fl.get("last_accessed"),
             fl.get("created", now_iso())),
        )

    for uid, fids in favorites.items():
        for fid in fids:
            await db._conn.execute(
                "INSERT OR IGNORE INTO favorites (user_id,file_id,created_at) VALUES (?,?,?)",
                (int(uid), fid, now_iso()),
            )

    await db._conn.commit()
    await db.close()
    print("✓ Migration complete. Original database.json was not modified.")
    print(f"  New SQLite DB: {config.DATABASE_PATH}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m app.migrate_json path/to/old/database.json")
        sys.exit(1)
    asyncio.run(migrate(sys.argv[1]))
