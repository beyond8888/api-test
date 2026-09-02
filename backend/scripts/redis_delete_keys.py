#!/usr/bin/env python
"""Delete Redis keys matching a pattern using SCAN (safe, non-blocking).

Usage:
    python redis_delete_keys.py

Edit the config block below to change host/port/password/pattern.
"""
import redis

# ── config ───────────────────────────────────────────────
REDIS_HOST = "r-2ze51da720bf2344.redis.rds.aliyuncs.com"
REDIS_PORT = 6379
REDIS_PWD = "V5*svVhGgH"
MATCH = "lgi-capacity:people_car_photo_reject:*"
COUNT = 100          # SCAN hint per iteration
BATCH_DELETE = True  # use UNLINK (async free) instead of DEL
# ─────────────────────────────────────────────────────────

def main():
    r = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PWD,
        decode_responses=True,
        socket_connect_timeout=10,
        socket_timeout=10,
    )

    # sanity check connection
    try:
        r.ping()
        print(f"[ok] connected to {REDIS_HOST}:{REDIS_PORT}")
    except Exception as e:
        print(f"[fail] cannot connect: {e}")
        return

    cursor = 0
    total = 0
    while True:
        cursor, keys = r.scan(cursor=cursor, match=MATCH, count=COUNT)
        if keys:
            # preview what will be deleted
            for k in keys:
                print(f"  - {k}")
            if BATCH_DELETE:
                r.unlink(*keys)   # non-blocking delete
            else:
                r.delete(*keys)
            total += len(keys)
        if cursor == 0:
            break

    print(f"[done] deleted {total} key(s) matching `{MATCH}`")


if __name__ == "__main__":
    main()
