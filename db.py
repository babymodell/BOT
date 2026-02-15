import sqlite3
import time
from typing import Tuple

DB_PATH = "casino.db"

def _conn():
    return sqlite3.connect(DB_PATH)

def init_db():
    with _conn() as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            balance INTEGER NOT NULL,
            last_daily INTEGER NOT NULL
        )
        """)
        con.commit()

def ensure_user(user_id: str):
    with _conn() as con:
        cur = con.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
        if cur.fetchone() is None:
            con.execute(
                "INSERT INTO users(user_id, balance, last_daily) VALUES (?, ?, ?)",
                (user_id, 1000, 0),
            )
            con.commit()

def get_user(user_id: str) -> Tuple[int, int]:
    ensure_user(user_id)
    with _conn() as con:
        cur = con.execute("SELECT balance, last_daily FROM users WHERE user_id=?", (user_id,))
        bal, last_daily = cur.fetchone()
        return int(bal), int(last_daily)

def set_balance(user_id: str, new_balance: int):
    ensure_user(user_id)
    with _conn() as con:
        con.execute("UPDATE users SET balance=? WHERE user_id=?", (int(new_balance), user_id))
        con.commit()

def set_last_daily(user_id: str, ts: int):
    ensure_user(user_id)
    with _conn() as con:
        con.execute("UPDATE users SET last_daily=? WHERE user_id=?", (int(ts), user_id))
        con.commit()
