import sqlite3
import json
import time
import uuid

db_file = 'DB/settings.db'

def create_database(db_file):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS settings (
        timestamp INTEGER NOT NULL,
        key VARCHAR NOT NULL,
        value VARCHAR
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uid TEXT UNIQUE NOT NULL,
        username TEXT NOT NULL,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'user',
        default_identity BOOLEAN DEFAULT 0
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS identities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        identity_name TEXT NOT NULL,
        uid TEXT UNIQUE NOT NULL,
        nickname TEXT NOT NULL
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS bookmarks (
        timestamp INTEGER NOT NULL,
        name VARCHAR NOT NULL,
        address VARCHAR NOT NULL,
        password VARCHAR,
        nickname VARCHAR
    )
    ''')

    conn.commit()
    conn.close()


    # Ensure there's a default identity
    create_default_identity()

def create_default_identity():
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM identities WHERE id=1")
    if cursor.fetchone() is None:
        cursor.execute('''
            INSERT INTO identities (identity_name, nickname, uid) VALUES (?, ?, ?)
        ''', ('Default', 'User', str(uuid.uuid4())))
        conn.commit()
    conn.close()

def load_default_identity(db_file=db_file):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT identity_name, nickname, uid FROM identities WHERE id=1")
    row = cursor.fetchone()
    conn.close()
    return {'identity_name': row[0], 'nickname': row[1], 'uid': row[2]} if row else None

def save_settings_to_db(settings):
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        cursor.execute('DELETE FROM settings')  # Radera befintliga inställningar
        for key, value in settings.items():
            cursor.execute('INSERT INTO settings (timestamp, key, value) VALUES (?, ?, ?)', (int(time.time()), key, json.dumps(value)))

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Failed to save settings to database: {str(e)}")

def load_settings_from_db():
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        cursor.execute('SELECT key, value FROM settings')
        rows = cursor.fetchall()

        settings = {}
        for row in rows:
            key, value = row
            if value is not None and value != "":
                settings[key] = json.loads(value)

        conn.close()
        return settings
    except Exception as e:
        print(f"Failed to load settings from database: {str(e)}")
        return {}
    
def load_bookmarks(db_file=db_file):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    cursor.execute('SELECT name, address, password, nickname FROM bookmarks')
    bookmarks = [{'name': row[0], 'address': row[1], 'password': row[2], 'nickname': row[3]} for row in cursor.fetchall()]
    
    conn.close()
    return bookmarks

def save_bookmarks(bookmarks, db_file=db_file):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM bookmarks')
    for bookmark in bookmarks:
        cursor.execute('INSERT INTO bookmarks (timestamp, name, address, password, nickname) VALUES (?, ?, ?, ?, ?)', (int(time.time()), bookmark['name'], bookmark['address'], bookmark['password'], bookmark['nickname']))
    
    conn.commit()
    conn.close()

# Skapa databasen om den inte redan finns
create_database(db_file)
