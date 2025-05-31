import json
import sqlite3

from utils.cuts_helper import sort_dawn_cuts, sort_obc_cuts

conn1 = sqlite3.connect("users.db")
conn2 = sqlite3.connect("runs.db")
conn3 = sqlite3.connect("schedule.db")
cursor1 = conn1.cursor()
cursor2 = conn2.cursor()
cursor3 = conn3.cursor()

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
    CREATE TABLE IF NOT EXISTS schedule (
        id TEXT PRIMARY KEY,
        date TEXT NOT NULL,  -- Stores date in DD/MM/YYYY
        time TEXT NOT NULL,   -- Stores time in HH:MM,
        difficulty TEXT NOT NULL,
        type TEXT NOT NULL,
        rl_id INTEGER NOT NULL,
        gc_id INTEGER NOT NULL,
        community TEXT NOT NULL
    )
    """
)
conn3.commit()


def get_user_stats(discord_id):
    cursor1.execute("SELECT balance, runs FROM users WHERE discord_id = ?", (discord_id,))
    result = cursor1.fetchone()
    return result if result else (0, 0)  # Default to (balance=0, runs=0) if not found


def get_top_users(stat, limit=5):
    query = f"SELECT discord_id, {stat} FROM users ORDER BY {stat} DESC LIMIT ?"
    cursor1.execute(query, (limit,))
    result = cursor1.fetchall()

    return result


def get_all_users():
    cursor1.execute("SELECT discord_id, balance, runs FROM users ORDER BY balance DESC")
    return cursor1.fetchall()


def update_user(discord_id, balance_increment, runs_increment=0):
    cursor1.execute(
        """
        INSERT OR IGNORE INTO users (discord_id, balance, runs)
        VALUES (?, 0, 0)
        """,
        (discord_id,),
    )

    # Then, update the balance and runs
    cursor1.execute(
        """
        UPDATE users
        SET balance = balance + ?, runs = runs + ?
        WHERE discord_id = ?
        """,
        (balance_increment, runs_increment, discord_id),
    )
    conn1.commit()


def add_schedule(id, date, time, difficulty, type, rl_id, gc_id, community):
    cursor3.execute(
        "INSERT INTO schedule (id, date, time, difficulty, type, rl_id, gc_id, community) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (id, date, time, difficulty, type, rl_id, gc_id, community),
    )
    conn3.commit()


def fetch_schedule():
    cursor3.execute(
        """
        SELECT id, date, time, difficulty, type, rl_id, gc_id, community
        FROM schedule 
        ORDER BY 
            SUBSTR(date, 7, 4) ASC,  -- Year
            SUBSTR(date, 4, 2) ASC,  -- Month
            SUBSTR(date, 1, 2) ASC,  -- Day
            time ASC  -- Time
        """
    )
    return cursor3.fetchall()


def schedule_exists(id):
    cursor3.execute(
        "SELECT id, date, time, difficulty, type, rl_id, gc_id, community FROM schedule WHERE id = ?",
        (id,),
    )
    run = cursor3.fetchone()
    return run  # Returns tuple (id, date, time, difficulty, type, rl_id, gc_id, community) or None if not found


def get_run_by_date_time(date: str, time: str):
    cursor3.execute(
        "SELECT * FROM schedule WHERE date = ? AND time = ?",
        (date, time),
    )
    run = cursor3.fetchone()
    return run


def remove_schedule(id):
    entry = schedule_exists(id)

    if not entry:
        return False  # Indicate that no entry was found

    # Delete the entry
    cursor3.execute("DELETE FROM schedule WHERE id = ?", (id,))
    conn3.commit()
    return True  # Indicate successful deletion


def get_all_runs():
    cursor2.execute("SELECT id, date, time, difficulty, type, pot, rl_id, gc_id, boosters, community, rl_cut_shared, gc_cut_shared FROM runs")
    return cursor2.fetchall()


def run_exists(id):
    cursor2.execute(
        "SELECT id, date, time, difficulty, type, pot, rl_id, gc_id, boosters, community, rl_cut_shared, gc_cut_shared FROM runs WHERE id = ?",
        (id,),
    )
    entry = cursor2.fetchone()
    return entry  # Returns tuple (id, date, time, difficulty, type, pot, rl_id, gc_id, boosters, community, rl_cut_shared, gc_cut_shared) or None if not found


def remove_run(id, bot):
    entry = run_exists(id)

    if not entry:
        return False  # Indicate that no entry was found

    # Delete the entry
    cursor2.execute("DELETE FROM runs WHERE id = ?", (id,))
    conn2.commit()
    (_, _, _, difficulty, type, pot, rl_id, gc_id, boosters, community, rl_cut_shared, gc_cut_shared) = entry
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
    boosters_json = json.dumps(boosters)

    cursor2.execute(
        """
        INSERT INTO runs (id, date, time, difficulty, type, pot, rl_id, gc_id, boosters, community, rl_cut_shared, gc_cut_shared)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (id, date, time, difficulty, type, pot, rl_id, gc_id, boosters_json, community, rl_cut_shared, gc_cut_shared),
    )

    # Commit the transaction
    conn2.commit()
    if community == "Dawn":
        booster_cut = sort_dawn_cuts(bot, difficulty, type, pot, rl_id, gc_id, boosters, rl_cut_shared, gc_cut_shared)
        return booster_cut
    elif community == "OBC":
        booster_cut = sort_obc_cuts(bot, difficulty, type, pot, rl_id, gc_id, boosters, rl_cut_shared, gc_cut_shared)
        return booster_cut
    else:
        print("Wrong community!")
        return None


def reset_dbs():
    cursor1.execute("DELETE FROM users")
    conn1.commit()
    cursor2.execute("DELETE FROM runs")
    conn2.commit()
    cursor3.execute("DELETE FROM schedule")
    conn3.commit()


def reset_sc():
    cursor3.execute("DELETE FROM schedule")
    conn3.commit()


def close_connection():
    conn1.close()
    conn2.close()
    conn3.close()
