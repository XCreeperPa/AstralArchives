import sqlite3
import secrets
import time
from pathlib import Path

DB_PATH = str(Path(__file__).parent.parent / "config" / "api_keys.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS api_keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        api_key TEXT UNIQUE NOT NULL,
        desc TEXT,
        created_at INTEGER,
        is_active INTEGER DEFAULT 1,
        total_tokens INTEGER DEFAULT 0,
        max_tokens INTEGER DEFAULT 100000,
        expire_at INTEGER DEFAULT 0  -- 新增过期时间字段
    )''')
    conn.commit()
    conn.close()

def add_api_key(desc: str = "", expire_at: int = 0) -> str:
    key = secrets.token_urlsafe(32)
    now = int(time.time())
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO api_keys (api_key, desc, created_at, expire_at) VALUES (?, ?, ?, ?)", (key, desc, now, expire_at))
    conn.commit()
    conn.close()
    return key

def check_api_key(key: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = int(time.time())
    c.execute("SELECT is_active, total_tokens, max_tokens, expire_at FROM api_keys WHERE api_key=?", (key,))
    row = c.fetchone()
    conn.close()
    if not row or not row[0]:
        return False
    if row[1] >= row[2]:
        return False
    if row[3] > 0 and row[3] < now:  # 检查是否过期
        return False
    return True

def add_token_usage(key: str, tokens: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE api_keys SET total_tokens = total_tokens + ? WHERE api_key=?", (tokens, key))
    conn.commit()
    conn.close()

def get_token_usage(key: str) -> int:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT total_tokens FROM api_keys WHERE api_key=?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

def get_key_status(key: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT is_active, total_tokens, max_tokens FROM api_keys WHERE api_key=?", (key,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return {'is_active': row[0], 'total_tokens': row[1], 'max_tokens': row[2]}

def disable_api_key(key: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE api_keys SET is_active=0 WHERE api_key=?", (key,))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="API Key 管理")
    parser.add_argument('--gen-key', type=str, help='生成新API-KEY并描述用途')
    parser.add_argument('--show-usage', type=str, help='查询某API-KEY的token用量')
    parser.add_argument('--set-max', nargs=2, metavar=('KEY','MAX'), help='设置某API-KEY最大用量')
    args = parser.parse_args()
    init_db()
    if args.gen_key:
        key = add_api_key(args.gen_key)
        print(f"新API-KEY: {key}")
    elif args.show_usage:
        usage = get_token_usage(args.show_usage)
        status = get_key_status(args.show_usage)
        if status:
            print(f"API-KEY {args.show_usage} 已用Token: {usage} / {status['max_tokens']}")
        else:
            print("API-KEY不存在")
    elif args.set_max:
        key, max_tokens = args.set_max
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("UPDATE api_keys SET max_tokens=? WHERE api_key=?", (int(max_tokens), key))
        conn.commit()
        conn.close()
        print(f"API-KEY {key} 最大用量已设为 {max_tokens}")
    else:
        print("无操作参数。--gen-key 或 --show-usage 或 --set-max")
