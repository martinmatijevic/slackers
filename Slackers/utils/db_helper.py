import json
import sqlite3

from utils.helper import update_cuts

conn1 = sqlite3.connect("users.db")
conn2 = sqlite3.connect("runs.db")
cursor1 = conn1.cursor()
cursor2 = conn2.cursor()

cursor1.execute(
    """
    CREATE TABLE IF NOT EXISTS users (
        discord_id INTEGER PRIMARY KEY,
        balance INTEGER DEFAULT 0,
        runs INTEGER DEFAULT 0
    )
    """
)
conn1.commit()

cursor2.execute(
    """
    CREATE TABLE IF NOT EXISTS runs (
        run_id TEXT PRIMARY KEY,
        run_date TEXT NOT NULL,  -- Stores date in DD/MM/YYYY
        run_time TEXT NOT NULL,   -- Stores time in HH:MM
        run_difficulty TEXT NOT NULL, 
        run_type TEXT NOT NULL,  
        run_pot INTEGER NOT NULL,
        rl_id INTEGER NOT NULL,
        gc_id INTEGER NOT NULL,
        user_ids TEXT NOT NULL  -- JSON array of user IDs
    )
"""
)
conn2.commit()


def update_user(discord_id, balance_increase=0, run_increase=0):
    cursor1.execute(
        """
        INSERT INTO users (discord_id, balance, runs) 
        VALUES (?, ?, ?)
        ON CONFLICT(discord_id) 
        DO UPDATE SET balance = balance + ?, runs = runs + ?
        """,
        (discord_id, balance_increase, run_increase, balance_increase, run_increase),
    )
    conn1.commit()


def add_run(
    run_id,
    run_pot,
    user_ids,
    run_date,
    run_time,
    run_difficulty,
    run_type,
    rl_id,
    gc_id,
):
    user_ids_json = json.dumps(user_ids)

    cursor2.execute(
        "INSERT INTO runs (run_id, run_date, run_time, run_difficulty, run_type, run_pot, rl_id, gc_id, user_ids) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            run_id,
            run_date,
            run_time,
            run_difficulty,
            run_type,
            run_pot,
            rl_id,
            gc_id,
            user_ids_json,
        ),
    )
    conn2.commit()

    update_cuts(
        user_ids,
        run_difficulty,
        run_type,
        run_pot,
        rl_id,
        gc_id,
        rl_cut_removed=False,
        gc_cut_removed=False,
        negative=False,
    )


def get_run(run_id: str):
    cursor2.execute(
        """
        SELECT user_ids, run_difficulty, run_type, run_pot, rl_id, gc_id
        FROM runs
        WHERE run_id = ?
        """,
        (run_id,),
    )

    row = cursor2.fetchone()

    if row:
        return {
            "user_ids": json.loads(row[0]),  # Convert JSON string to list
            "run_difficulty": row[1],
            "run_type": row[2],
            "run_pot": row[3],
            "rl_id": row[4],
            "gc_id": row[5],
        }

    return None  # Return None if run_id is not found


def update_run(
    run_id: str,
    user_ids,
    run_difficulty,
    run_type,
    run_pot,
    rl_id,
    gc_id,
    rl_cut_removed,
    gc_cut_removed,
):
    old_data = get_run(run_id)
    update_cuts(
        old_data["user_ids"],
        old_data["run_difficulty"],
        old_data["run_type"],
        old_data["run_pot"],
        old_data["rl_id"],
        old_data["gc_id"],
        rl_cut_removed=False,
        gc_cut_removed=False,
        negative=True,
    )
    cursor2.execute(
        """
        UPDATE runs 
        SET user_ids = ?, run_difficulty = ?, run_type = ?, run_pot = ?, rl_id = ?, gc_id = ? 
        WHERE run_id = ?
        """,
        (json.dumps(user_ids), run_difficulty, run_type, run_pot, rl_id, gc_id, run_id),
    )
    conn2.commit()
    if rl_cut_removed:
        update_cuts(
            user_ids,
            run_difficulty,
            run_type,
            run_pot,
            rl_id,
            gc_id,
            rl_cut_removed=True,
            gc_cut_removed=False,
            negative=False,
        )
    elif gc_cut_removed:
        update_cuts(
            user_ids,
            run_difficulty,
            run_type,
            run_pot,
            rl_id,
            gc_id,
            rl_cut_removed=False,
            gc_cut_removed=True,
            negative=False,
        )
    else:
        update_cuts(
            user_ids,
            run_difficulty,
            run_type,
            run_pot,
            rl_id,
            gc_id,
            rl_cut_removed=False,
            gc_cut_removed=False,
            negative=False,
        )


def del_run(run_id: str, user_ids, run_difficulty, run_type, run_pot, rl_id, gc_id):
    cursor2.execute("DELETE FROM runs WHERE run_id = ?", (run_id,))
    conn2.commit()
    update_cuts(
        user_ids,
        run_difficulty,
        run_type,
        run_pot,
        rl_id,
        gc_id,
        rl_cut_removed=False,
        gc_cut_removed=False,
        negative=True,
    )


def get_user_stats(discord_id):
    cursor1.execute(
        "SELECT balance, runs FROM users WHERE discord_id = ?", (discord_id,)
    )
    result = cursor1.fetchone()
    return result if result else (0, 0)  # Default to (balance=0, runs=0) if not found


def reset_dbs():
    cursor1.execute("DELETE FROM users")
    conn1.commit()
    cursor2.execute("DELETE FROM runs")
    conn2.commit()


def get_all_users():
    cursor1.execute("SELECT discord_id, balance, runs FROM users")
    return cursor1.fetchall()


def get_all_runs():
    cursor2.execute(
        "SELECT run_id, run_date, run_time, run_difficulty, run_type, run_pot, rl_id, gc_id, user_ids FROM runs"
    )
    return cursor2.fetchall()


def get_top_users(stat, limit=5):
    query = f"SELECT discord_id, {stat} FROM users ORDER BY {stat} DESC LIMIT ?"
    cursor1.execute(query, (limit,))
    result = cursor1.fetchall()

    return result


def close_connection():
    conn1.close()
    conn2.close()
