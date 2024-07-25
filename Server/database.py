import sqlite3
import json
import secrets
import hashlib
import logging

def init_db(db_file):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uid TEXT UNIQUE NOT NULL,
        username TEXT NOT NULL,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'user',
        is_superadmin BOOLEAN DEFAULT 0
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

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS privilege_keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT UNIQUE NOT NULL,
        role TEXT NOT NULL,
        description TEXT
    )
    ''')

    conn.commit()
    conn.close()

def ensure_default_rooms(db_file):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM rooms WHERE name='Lobby'")
    room = cursor.fetchone()

    if not room:
        cursor.execute("INSERT INTO rooms (name, members) VALUES (?, ?)", ('Lobby', json.dumps([])))
        conn.commit()

    conn.close()

def create_initial_admin(db_file):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE is_superadmin=1")
    admin = cursor.fetchone()

    if not admin:
        admin_username = 'admin'
        admin_password = secrets.token_urlsafe(16)
        hashed_password = hashlib.sha256(admin_password.encode()).hexdigest()
        cursor.execute("INSERT INTO users (uid, username, password, role, is_superadmin) VALUES (?, ?, ?, ?, ?)",
                       (secrets.token_hex(16), admin_username, hashed_password, 'superadmin', True))
        conn.commit()
        print(f"Admin created with username: {admin_username} and password: {admin_password}")
        logging.info(f"Admin created with username: {admin_username} and password: {admin_password}")

    conn.close()

def create_initial_privilege_key(db_file):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM privilege_keys WHERE role='superadmin'")
    key = cursor.fetchone()

    if not key:
        privilege_key = secrets.token_urlsafe(24)
        cursor.execute("INSERT INTO privilege_keys (key, role, description) VALUES (?, ?, ?)",
                       (privilege_key, 'superadmin', 'Initial server admin privilege key'))
        conn.commit()
        print(f"Privilege key for server admin: {privilege_key}")
        logging.info(f"Privilege key for server admin: {privilege_key}")

    conn.close()

def get_db_connection(db_file):
    return sqlite3.connect(db_file)
