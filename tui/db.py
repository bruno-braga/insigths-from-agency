import sqlite3
import os

DB_PATH = os.environ.get("DB_PATH", "data/origin.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = _connect()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS agents (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            model TEXT NOT NULL,
            instructions TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def get_all_agents() -> list[dict]:
    conn = _connect()
    rows = conn.execute("SELECT id, name, model, instructions FROM agents").fetchall()
    conn.close()
    return [dict(row) for row in rows]


def insert_agent(agent_id: str, name: str, model: str, instructions: str) -> None:
    conn = _connect()
    conn.execute(
        "INSERT INTO agents (id, name, model, instructions) VALUES (?, ?, ?, ?)",
        (agent_id, name, model, instructions),
    )
    conn.commit()
    conn.close()


def update_agent(agent_id: str, name: str, model: str, instructions: str) -> None:
    conn = _connect()
    conn.execute(
        "UPDATE agents SET name = ?, model = ?, instructions = ? WHERE id = ?",
        (name, model, instructions, agent_id),
    )
    conn.commit()
    conn.close()


def delete_agent(agent_id: str) -> None:
    conn = _connect()
    conn.execute("DELETE FROM agents WHERE id = ?", (agent_id,))
    conn.commit()
    conn.close()
