import sqlite3
import json

def init_db(db_file):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        uuid TEXT UNIQUE NOT NULL,
        role TEXT DEFAULT 'user'
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS rooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        password TEXT,
        members TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_id INTEGER,
        user_id INTEGER,
        message TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (room_id) REFERENCES rooms (id),
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS bans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        reason TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')

    conn.commit()
    conn.close()

def ensure_default_rooms(db_file):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # Kontrollera om rummet "Lobby" finns, annars skapa det
    cursor.execute("SELECT * FROM rooms WHERE name='Lobby'")
    room = cursor.fetchone()

    if not room:
        cursor.execute("INSERT INTO rooms (name, members) VALUES (?, ?)", ('Lobby', json.dumps([])))
        conn.commit()

    conn.close()

def get_db_connection(db_file):
    return sqlite3.connect(db_file)
