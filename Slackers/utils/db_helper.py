import json
import os
import sqlite3

from utils.cuts_helper import sort_dawn_cuts, sort_obc_cuts

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "..", "users_tww_s2.db")
conn1 = sqlite3.connect(DB_PATH)
DB_PATH2 = os.path.join(BASE_DIR, "..", "runs_tww_s2.db")
conn2 = sqlite3.connect(DB_PATH2)
DB_PATH3 = os.path.join(BASE_DIR, "..", "users_tww_s3.db")
conn3 = sqlite3.connect(DB_PATH3)
DB_PATH4 = os.path.join(BASE_DIR, "..", "runs_tww_s3.db")
conn4 = sqlite3.connect(DB_PATH4)

cursor1 = conn1.cursor()
cursor2 = conn2.cursor()
cursor3 = conn3.cursor()
cursor4 = conn4.cursor()

cursor1.execute(
    """
    CREATE TABLE IF NOT EXISTS users_tww_s2 (
        discord_id INTEGER PRIMARY KEY,
        balance INTEGER DEFAULT 0,
        runs INTEGER DEFAULT 0
    )
    """
)
conn1.commit()

cursor2.execute(
    """
    CREATE TABLE IF NOT EXISTS runs_tww_s2 (
        id TEXT PRIMARY KEY,
        date TEXT NOT NULL,  -- Stores date in DD/MM/YYYY
        time TEXT NOT NULL,   -- Stores time in HH:MM
        difficulty TEXT NOT NULL, 
        type TEXT NOT NULL,  
        pot INTEGER NOT NULL,
        rl_id INTEGER NOT NULL,
        gc_id INTEGER NOT NULL,
        boosters TEXT NOT NULL,  -- JSON array of user IDs
        community TEXT NOT NULL,
        rl_cut_shared INTEGER NOT NULL DEFAULT 0, -- 0 = false, 1 = true
        gc_cut_shared INTEGER NOT NULL DEFAULT 0 -- 0 = false, 1 = true
    )
    """
)
conn2.commit()

cursor3.execute(
    """
    CREATE TABLE IF NOT EXISTS users_tww_s3 (
        discord_id INTEGER PRIMARY KEY,
        balance INTEGER DEFAULT 0,
        runs INTEGER DEFAULT 0
    )
    """
)
conn3.commit()

cursor4.execute(
    """
    CREATE TABLE IF NOT EXISTS runs_tww_s3 (
        id TEXT PRIMARY KEY,
        date TEXT NOT NULL,  -- Stores date in DD/MM/YYYY
        time TEXT NOT NULL,   -- Stores time in HH:MM
        difficulty TEXT NOT NULL, 
        type TEXT NOT NULL,  
        pot INTEGER NOT NULL,
        rl_id INTEGER NOT NULL,
        gc_id INTEGER NOT NULL,
        boosters TEXT NOT NULL,  -- JSON array of user IDs
        community TEXT NOT NULL,
        rl_cut_shared INTEGER NOT NULL DEFAULT 0, -- 0 = false, 1 = true
        gc_cut_shared INTEGER NOT NULL DEFAULT 0 -- 0 = false, 1 = true
    )
    """
)
conn4.commit()


def get_user_stats(discord_id, season):
    if season == "TWW-S2":
        cursor1.execute("SELECT balance, runs FROM users_tww_s2 WHERE discord_id = ?", (discord_id,))
        result = cursor1.fetchone()
    elif season == "TWW-S3":
        cursor3.execute("SELECT balance, runs FROM users_tww_s3 WHERE discord_id = ?", (discord_id,))
        result = cursor3.fetchone()
    return result if result else (0, 0)  # Default to (balance=0, runs=0) if not found


def get_top_users(season, stat, limit=5):
    if season == "TWW-S2":
        query = f"SELECT discord_id, {stat} FROM users_tww_s2 ORDER BY {stat} DESC LIMIT ?"
        cursor1.execute(query, (limit,))
        return cursor1.fetchall()
    elif season == "TWW-S3":
        query = f"SELECT discord_id, {stat} FROM users_tww_s3 ORDER BY {stat} DESC LIMIT ?"
        cursor3.execute(query, (limit,))
        return cursor3.fetchall()
    else:
        return None


def get_all_users(season):
    if season == "TWW-S2":
        cursor1.execute("SELECT discord_id, balance, runs FROM users_tww_s2 ORDER BY balance DESC")
        return cursor1.fetchall()
    elif season == "TWW-S3":
        cursor3.execute("SELECT discord_id, balance, runs FROM users_tww_s3 ORDER BY balance DESC")
        return cursor3.fetchall()
    else:
        return None


def update_user(discord_id, balance_increment, runs_increment=0):
    cursor3.execute(
        """
        INSERT OR IGNORE INTO users_tww_s3 (discord_id, balance, runs)
        VALUES (?, 0, 0)
        """,
        (discord_id,),
    )

    # Then, update the balance and runs
    cursor3.execute(
        """
        UPDATE users_tww_s3
        SET balance = balance + ?, runs = runs + ?
        WHERE discord_id = ?
        """,
        (balance_increment, runs_increment, discord_id),
    )
    conn3.commit()


def get_all_runs(season):
    if season == "TWW-S2":
        cursor2.execute("SELECT id, date, time, difficulty, type, pot, rl_id, gc_id, boosters, community, rl_cut_shared, gc_cut_shared FROM runs_tww_s2")
        return cursor2.fetchall()
    elif season == "TWW-S3":
        cursor4.execute("SELECT id, date, time, difficulty, type, pot, rl_id, gc_id, boosters, community, rl_cut_shared, gc_cut_shared FROM runs_tww_s3")
        return cursor4.fetchall()
    else:
        return None


def run_exists(id):
    cursor4.execute(
        "SELECT difficulty, type, pot, rl_id, gc_id, boosters, community, rl_cut_shared, gc_cut_shared FROM runs_tww_s3 WHERE id = ?",
        (id,),
    )
    entry = cursor4.fetchone()
    return entry  # Returns tuple (difficulty, type, pot, rl_id, gc_id, boosters, community, rl_cut_shared, gc_cut_shared) or None if not found


def remove_run(id, bot):
    entry = run_exists(id)

    if not entry:
        return False  # Indicate that no entry was found

    # Delete the entry
    cursor4.execute("DELETE FROM runs_tww_s3 WHERE id = ?", (id,))
    conn4.commit()
    (difficulty, type, pot, rl_id, gc_id, boosters, community, rl_cut_shared, gc_cut_shared) = entry
    boosters_dict = {int(k): v for k, v in json.loads(boosters).items()}
    if community == "Dawn":
        sort_dawn_cuts(bot, difficulty, type, pot, rl_id, gc_id, boosters_dict, rl_cut_shared, gc_cut_shared, negative=1)
    elif community == "OBC":
        sort_obc_cuts(bot, difficulty, type, pot, rl_id, gc_id, boosters_dict, rl_cut_shared, gc_cut_shared, negative=1)
    else:
        print("Wrong community!")
    return True  # Indicate successful deletion


def add_run(bot, id, date, time, difficulty, type, pot, rl_id, gc_id, boosters, community, rl_cut_shared=0, gc_cut_shared=0):
    # Convert the list of integers to a JSON array (which will be a string representation of the list)
    try:
        boosters_json = json.dumps(boosters)

        cursor4.execute(
            """
            INSERT INTO runs_tww_s3 (id, date, time, difficulty, type, pot, rl_id, gc_id, boosters, community, rl_cut_shared, gc_cut_shared)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (id, date, time, difficulty, type, pot, rl_id, gc_id, boosters_json, community, rl_cut_shared, gc_cut_shared),
        )

        # Commit the transaction
        conn4.commit()
        if community == "Dawn":
            booster_cut = sort_dawn_cuts(bot, difficulty, type, pot, rl_id, gc_id, boosters, rl_cut_shared, gc_cut_shared)
            return booster_cut
        elif community == "OBC":
            booster_cut = sort_obc_cuts(bot, difficulty, type, pot, rl_id, gc_id, boosters, rl_cut_shared, gc_cut_shared)
            return booster_cut
        else:
            print("Wrong community!")
            return None

    except Exception as e:
        print(f"Error: {e}")


def reset_dbs():
    cursor3.execute("DELETE FROM users_tww_s3")
    conn3.commit()
    cursor4.execute("DELETE FROM runs_tww_s3")
    conn4.commit()


def close_connection():
    conn1.close()
    conn2.close()
    conn3.close()
    conn4.close()
