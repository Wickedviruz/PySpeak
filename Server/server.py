import asyncio
import websockets
import json
import sqlite3
import uuid
import logging
import ssl
from database import init_db, ensure_default_rooms, create_initial_admin, create_initial_privilege_key

# Local imports
import database
import backup
import config_loader

clients = {}

# loads the config file
config = config_loader.load_config('config.json')

# Extract server settings
server_address = config.get('server', {}).get('server_address', 'localhost')
port = config.get('server', {}).get('port', 8765)
server_password = config.get('server', {}).get('server_password', None)
server_name = config.get('server', {}).get('server_name', 'PyServ')
welcome_message = config.get('server', {}).get('welcome_message', "Welcome to the server! Enjoy your stay.")
max_users = config.get('server', {}).get('max_users', 100)

# Extract database settings
db_file = config.get('database', {}).get('db_file', 'DB/pyspeak.db')

# Extract logging settings
log_level = config.get('logging', {}).get('level', 'INFO').upper()
log_file = config.get('logging', {}).get('log_file', 'server.log')

# Extract security settings
use_ssl = config.get('security', {}).get('use_ssl', False)
ssl_certfile = config.get('security', {}).get('ssl_certfile', 'cert.pem')
ssl_keyfile = config.get('security', {}).get('ssl_keyfile', 'key.pem')

# Extract rate limiting settings
rate_limiting_enabled = config.get('rate_limiting', {}).get('enabled', True)
max_requests_per_minute = config.get('rate_limiting', {}).get('max_requests_per_minute', 60)

# Extract room settings
default_room = config.get('rooms', {}).get('default_room', 'Lobby')
default_room_password = config.get('rooms', {}).get('default_room_password', None)

# Extract backup settings
backup_enabled = config.get('backup', {}).get('enabled', True)
backup_interval_minutes = config.get('backup', {}).get('backup_interval_minutes', 1440)
backup_folder = config.get('backup', {}).get('backup_folder', 'backups/')

# Creates the logfile 
logging.basicConfig(filename=log_file, level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')
logging.info('Server started')

def get_db_connection():
    return sqlite3.connect(db_file)

async def handler(websocket, path):
    client_id = str(uuid.uuid4())
    clients[client_id] = {'websocket': websocket, 'room': None, 'username': None}

    try:
        async for message in websocket:
            if isinstance(message, bytes):
                await handle_audio(client_id, message)
            else:
                data = json.loads(message)
                await process_message(client_id, data)
    except websockets.ConnectionClosed:
        print(f"Client {client_id} disconnected")
    finally:
        await remove_client_from_room(client_id)

async def remove_client_from_room(client_id):
    if client_id in clients and clients[client_id]['room']:
        room_name = clients[client_id]['room']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT members FROM rooms WHERE name=?", (room_name,))
        members = json.loads(cursor.fetchone()[0])
        if client_id in members:
            members.remove(client_id)
            cursor.execute("UPDATE rooms SET members=? WHERE name=?", (json.dumps(members), room_name))
            conn.commit()
            await update_room_members(room_name)
            await update_room_list()
        conn.close()
    if client_id in clients:
        del clients[client_id]

async def process_message(client_id, data):
    message_type = data['type']

    if message_type == 'join':
        await handle_join(client_id, data, first_time=True)
    elif message_type == 'message':
        await handle_message(client_id, data)
    elif message_type == 'switch_room':
        await handle_switch_room(client_id, data)
    elif message_type == 'create_channel':
        await handle_create_room(client_id, data)
    elif message_type == 'edit_channel':
        await handle_edit_room(client_id, data)
    elif message_type == 'delete_channel':
        await handle_delete_room(client_id, data)
    elif message_type == 'audio':
        await handle_audio(client_id, data)
    elif message_type == 'talking':
        await handle_talking(client_id, data)
    elif message_type == 'private_message':
        await handle_private_message(client_id, data)
    elif message_type == 'ban':
        await handle_ban(client_id, data)
    elif message_type == 'kick':
        await handle_kick(client_id, data)
    elif message_type == 'use_privilege_key':
        await handle_use_privilege_key(client_id, data)

async def handle_join(client_id, data, first_time=False):
    username = data['username']
    uid = data['uid']
    room_name = data.get('room', 'Lobby')

    if server_password and server_password != data.get('password'):
        await clients[client_id]['websocket'].send(json.dumps({'type': 'error', 'message': 'Invalid server password'}))
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE uid=?", (uid,))
    user = cursor.fetchone()

    if not user:
        cursor.execute("INSERT INTO users (uid, username, password, role, is_superadmin) VALUES (?, ?, ?, ?, ?)",
                       (uid, username, 'default_password', 'user', False))
        conn.commit()
        cursor.execute("SELECT * FROM users WHERE uid=?", (uid,))
        user = cursor.fetchone()

    clients[client_id]['username'] = username
    clients[client_id]['uid'] = uid
    clients[client_id]['role'] = user[4]  # Assuming role is the 5th column

    cursor.execute("SELECT * FROM rooms WHERE name=?", (room_name,))
    room = cursor.fetchone()

    if not room:
        cursor.execute("INSERT INTO rooms (name, members) VALUES (?, ?)", (room_name, json.dumps([])))
        conn.commit()
        cursor.execute("SELECT * FROM rooms WHERE name=?", (room_name,))
        room = cursor.fetchone()

    members = json.loads(room[3])
    members.append(client_id)
    cursor.execute("UPDATE rooms SET members=? WHERE name=?", (json.dumps(members), room_name))
    conn.commit()

    clients[client_id]['room'] = room_name

    if first_time:
        await clients[client_id]['websocket'].send(json.dumps({'type': 'info', 'message': welcome_message}))

    await clients[client_id]['websocket'].send(json.dumps({
        'type': 'info',
        'message': f"Welcome to {room_name}, {username}!",
        'role': user[4]  # Skicka användarens roll till klienten
    }))

    conn.close()
    await update_room_members(room_name)
    await update_room_list()

async def handle_audio(client_id, audio_data):
    room_name = clients[client_id]['room']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT members FROM rooms WHERE name=?", (room_name,))
    members = json.loads(cursor.fetchone()[0])
    
    for member_id in members:
        if member_id != client_id and clients[member_id]['websocket'].open:
            await clients[member_id]['websocket'].send(audio_data)
    conn.close()

async def handle_talking(client_id, data):
    room_name = clients[client_id]['room']
    is_talking = data['status']
    username = clients[client_id]['username']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT members FROM rooms WHERE name=?", (room_name,))
    members = json.loads(cursor.fetchone()[0])

    for member_id in members:
        if clients[member_id]['websocket'].open:
            await clients[member_id]['websocket'].send(json.dumps({'type': 'talking', 'username': username, 'status': is_talking}))
    conn.close()

async def handle_message(client_id, data):
    room_name = clients[client_id]['room']
    message = data['message']
    username = clients[client_id]['username']

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM rooms WHERE name=?", (room_name,))
    room_id = cursor.fetchone()[0]
    cursor.execute("SELECT id FROM users WHERE username=?", (username,))
    user_id = cursor.fetchone()[0]

    cursor.execute("INSERT INTO messages (room_id, user_id, message) VALUES (?, ?, ?)", (room_id, user_id, message))
    conn.commit()

    cursor.execute("SELECT members FROM rooms WHERE name=?", (room_name,))
    members = json.loads(cursor.fetchone()[0])

    for member_id in members:
        if clients[member_id]['websocket'].open:
            await clients[member_id]['websocket'].send(json.dumps({'type': 'message', 'username': username, 'message': message}))
    conn.close()

async def handle_private_message(client_id, data):
    recipient = data['recipient']
    message = data['message']
    username = clients[client_id]['username']

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT uid FROM users WHERE username=?", (recipient,))
    recipient_uid = cursor.fetchone()

    if recipient_uid:
        recipient_uid = recipient_uid[0]
        if recipient_uid in clients and clients[recipient_uid]['websocket'].open:
            await clients[recipient_uid]['websocket'].send(json.dumps({'type': 'private_message', 'username': username, 'message': message}))
    conn.close()

async def handle_switch_room(client_id, data):
    new_room_name = data['new_room']
    current_room_name = clients[client_id]['room']
    room_password = data.get('room_password', None)

    if new_room_name == current_room_name:
        await clients[client_id]['websocket'].send(json.dumps({'type': 'error', 'message': f"You are already in {new_room_name}."}))
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    # Kontrollera om det nya rummet finns
    cursor.execute("SELECT * FROM rooms WHERE name=?", (new_room_name,))
    room = cursor.fetchone()

    if not room:
        await clients[client_id]['websocket'].send(json.dumps({'type': 'error', 'message': f"Room {new_room_name} does not exist."}))
        conn.close()
        return

    # Kontrollera lösenord om det finns
    if room[2] and room[2] != room_password:
        await clients[client_id]['websocket'].send(json.dumps({'type': 'password_required', 'room': new_room_name}))
        conn.close()
        return

    # Ta bort användaren från det nuvarande rummet
    if current_room_name:
        cursor.execute("SELECT members FROM rooms WHERE name=?", (current_room_name,))
        current_room_members = json.loads(cursor.fetchone()[0])
        if client_id in current_room_members:
            current_room_members.remove(client_id)
            cursor.execute("UPDATE rooms SET members=? WHERE name=?", (json.dumps(current_room_members), current_room_name))
            await update_room_members(current_room_name)

    # Lägg till användaren i det nya rummet
    cursor.execute("SELECT members FROM rooms WHERE name=?", (new_room_name,))
    new_room_members = json.loads(cursor.fetchone()[0])
    new_room_members.append(client_id)
    cursor.execute("UPDATE rooms SET members=? WHERE name=?", (json.dumps(new_room_members), new_room_name))
    conn.commit()

    clients[client_id]['room'] = new_room_name
    await update_room_members(new_room_name)

    conn.close()

    # Skicka uppdatering om rumsbytet till klienten
    await clients[client_id]['websocket'].send(json.dumps({'type': 'switched_room', 'message': f'Switched to room: {new_room_name}'}))
    await update_room_list()

async def handle_create_room(client_id, data):
    if clients[client_id]['role'] not in ['admin', 'superadmin']:
        await clients[client_id]['websocket'].send(json.dumps({'type': 'error', 'message': 'You do not have permission to create rooms.'}))
        return

    room_name = data['room_name']
    room_password = data.get('room_password', None)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM rooms WHERE name=?", (room_name,))
    room = cursor.fetchone()

    if room:
        await clients[client_id]['websocket'].send(json.dumps({'type': 'error', 'message': f"Room {room_name} already exists."}))
    else:
        cursor.execute("INSERT INTO rooms (name, password, members) VALUES (?, ?, ?)", (room_name, room_password, json.dumps([])))
        conn.commit()
        await clients[client_id]['websocket'].send(json.dumps({'type': 'info', 'message': f"Room {room_name} created."}))
        await update_room_list()
    conn.close()

async def handle_edit_room(client_id, data):
    if not await is_admin(client_id):
        await clients[client_id]['websocket'].send(json.dumps({'type': 'error', 'message': 'You do not have permission to edit rooms.'}))
        return

    room_name = data['room_name']
    room_password = data.get('room_password', None)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM rooms WHERE name=?", (room_name,))
    room = cursor.fetchone()

    if room:
        cursor.execute("UPDATE rooms SET password=? WHERE name=?", (room_password, room_name))
        conn.commit()
        await clients[client_id]['websocket'].send(json.dumps({'type': 'info', 'message': f"Room {room_name} updated."}))
        await update_room_list()
    else:
        await clients[client_id]['websocket'].send(json.dumps({'type': 'error', 'message': f"Room {room_name} does not exist."}))
    conn.close()

async def handle_delete_room(client_id, data):
    if not await is_admin(client_id):
        await clients[client_id]['websocket'].send(json.dumps({'type': 'error', 'message': 'You do not have permission to delete rooms.'}))
        return

    room_name = data['room_name']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM rooms WHERE name=?", (room_name,))
    room = cursor.fetchone()

    if room:
        cursor.execute("DELETE FROM rooms WHERE name=?", (room_name,))
        conn.commit()
        await clients[client_id]['websocket'].send(json.dumps({'type': 'info', 'message': f"Room {room_name} deleted."}))
        await update_room_list()
    else:
        await clients[client_id]['websocket'].send(json.dumps({'type': 'error', 'message': f"Room {room_name} does not exist."}))
    conn.close()


async def handle_ban(client_id, data):
    if not await is_admin(client_id):
        await clients[client_id]['websocket'].send(json.dumps({'type': 'error', 'message': 'You do not have permission to ban users.'}))
        return

    username_to_ban = data['username']
    reason = data.get('reason', 'No reason provided')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username=?", (username_to_ban,))
    user_id_to_ban = cursor.fetchone()

    if user_id_to_ban:
        user_id_to_ban = user_id_to_ban[0]
        cursor.execute("INSERT INTO bans (user_id, reason) VALUES (?, ?)", (user_id_to_ban, reason))
        conn.commit()
        await clients[client_id]['websocket'].send(json.dumps({'type': 'info', 'message': f"{username_to_ban} has been banned."}))

        for uid, client in clients.items():
            if client['username'] == username_to_ban:
                await remove_client_from_room(uid)
                await client['websocket'].close()
    else:
        await clients[client_id]['websocket'].send(json.dumps({'type': 'error', 'message': f"User {username_to_ban} not found."}))
    conn.close()

async def handle_kick(client_id, data):
    if not await is_admin(client_id):
        await clients[client_id]['websocket'].send(json.dumps({'type': 'error', 'message': 'You do not have permission to kick users.'}))
        return

    username_to_kick = data['username']
    reason = data.get('reason', 'No reason provided')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT uid FROM users WHERE username=?", (username_to_kick,))
    user_uid_to_kick = cursor.fetchone()

    if user_uid_to_kick:
        user_uid_to_kick = user_uid_to_kick[0]
        await clients[client_id]['websocket'].send(json.dumps({'type': 'info', 'message': f"{username_to_kick} has been kicked."}))

        if user_uid_to_kick in clients:
            await remove_client_from_room(user_uid_to_kick)
            await clients[user_uid_to_kick]['websocket'].close()
    else:
        await clients[client_id]['websocket'].send(json.dumps({'type': 'error', 'message': f"User {username_to_kick} not found."}))
    conn.close()

async def handle_use_privilege_key(client_id, data):
    privilege_key = data['key']

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT role FROM privilege_keys WHERE key=?", (privilege_key,))
    result = cursor.fetchone()

    if result:
        role = result[0]
        cursor.execute("UPDATE users SET role=? WHERE uid=?", (role, clients[client_id]['uid']))
        conn.commit()
        clients[client_id]['role'] = role  # Update role in clients dictionary
        await clients[client_id]['websocket'].send(json.dumps({'type': 'info', 'message': f'Privilege key used. Role updated to {role}.'}))
    else:
        await clients[client_id]['websocket'].send(json.dumps({'type': 'error', 'message': 'Invalid privilege key.'}))

    conn.close()

def get_user_role(uid):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT role FROM users WHERE uid=?", (uid,))
    role = cursor.fetchone()
    conn.close()
    return role[0] if role else None

async def is_admin(client_id):
    uid = clients[client_id]['uid']
    role = get_user_role(uid)
    return role in ['admin', 'superadmin']

async def update_room_members(room_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT members FROM rooms WHERE name=?", (room_name,))
    members = json.loads(cursor.fetchone()[0])
    
    # Endast inkludera medlemmar som fortfarande är anslutna
    member_details = [{'username': clients[client_id]['username'], 'id': client_id} for client_id in members if client_id in clients]

    for member_id in members:
        if member_id in clients and clients[member_id]['websocket'].open:
            await clients[member_id]['websocket'].send(json.dumps({'type': 'room_update', 'members': member_details}))
    conn.close()

async def update_room_list():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, password, members FROM rooms")
    rooms = cursor.fetchall()
    
    room_list = {}
    for room in rooms:
        room_name = room[0]
        room_password = room[1]
        room_members = json.loads(room[2])
        
        # Endast inkludera medlemmar som fortfarande är anslutna
        valid_members = [clients[client_id]['username'] for client_id in room_members if client_id in clients]
        room_list[room_name] = {'members': valid_members, 'password': room_password}
    
    for client in clients.values():
        if client['websocket'].open:
            await client['websocket'].send(json.dumps({'type': 'room_list', 'rooms': room_list, 'server_name': server_name}))
    conn.close()

async def main():
    database.init_db(db_file)
    database.ensure_default_rooms(db_file)
    database.create_initial_admin(db_file)
    database.create_initial_privilege_key(db_file)

    if use_ssl:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(certfile=ssl_certfile, keyfile=ssl_keyfile)
        server = await websockets.serve(handler, server_address, port, ssl=ssl_context)
        print(f"Server started on wss://{server_address}:{port}")
    else:
        server = await websockets.serve(handler, server_address, port)
        print(f"Server started on ws://{server_address}:{port}")

    if backup_enabled:
        asyncio.create_task(backup.backup_database(db_file, backup_folder, backup_interval_minutes))

    await server.wait_closed()

if __name__ == '__main__':
    asyncio.run(main())
