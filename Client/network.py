import asyncio
import json
import websockets

async def connect_to_server(client, server_address, password, name):
    try:
        client.log_message(f"Trying to connect to server on {server_address}")
        client.websocket = await websockets.connect(f'ws://{server_address}')
        
        await client.websocket.send(json.dumps({'type': 'join', 'username': name, 'password': password}))
        client.log_message(f"Connected to {server_address} as {name}")
        client.current_username = name
        client.play_sound('assets/sound/connected.wav')

        asyncio.ensure_future(receive_messages(client))
    except Exception as e:
        client.log_message(f"Failed to connect: {str(e)}")

async def disconnect_from_server(client):
    if client.websocket:
        await client.websocket.close()
        client.websocket = None
        client.log_message("Disconnected from server")
        client.play_sound('assets/sound/disconnected.wav')
        client.roomList.clear()
        client.userInfo.clear()

async def receive_messages(client):
    try:
        async for message in client.websocket:
            if isinstance(message, bytes):
                client.play_audio(message)
            else:
                data = json.loads(message)
                if data['type'] == 'info':
                    client.log_message(data['message'])
                elif data['type'] == 'message':
                    client.log_message(f"{data['username']}: {data['message']}")
                elif data['type'] == 'room_update':
                    client.update_room_members(data['members'])
                elif data['type'] == 'room_list':
                    client.update_room_list(data)
                elif data['type'] == 'error':
                    client.log_message(f"Error: {data['message']}")
                elif data['type'] == 'talking':
                    client.update_talking_status(data['username'], data['status'])
    except websockets.ConnectionClosed:
        client.log_message("Connection closed")
