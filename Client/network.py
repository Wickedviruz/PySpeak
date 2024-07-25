import asyncio
import json
import websockets
import datetime

async def connect_to_server(self, server_address, password, name):
    try:
        self.log_message(f"trying to connect to server on {server_address}")
        self.websocket = await websockets.connect(f'ws://{server_address}')
        await self.websocket.send(json.dumps({'type': 'join', 'username': name, 'password': password}))
        self.log_message(f"Connected to {server_address} as {name}")
        self.current_username = name
        self.connection_start_time = datetime.now()
        self.ping = 0
        self.connectionInfoAction.setEnabled(True)
        self.update_bookmark_actions()
        self.play_sound('assets/sound/connected.wav')

        asyncio.ensure_future(self.receive_messages())
    except Exception as e:
        self.log_message(f"Failed to connect: {str(e)}")

async def disconnect_from_server(self):
    if self.websocket:
        await self.websocket.close()
        self.websocket = None
        self.connectionInfoAction.setEnabled(False)
        self.log_message("Disconnected from server")
        self.play_sound('assets/sound/disconnected.wav')
        self.update_bookmark_actions()
        self.roomList.clear()
        self.userInfo.clear()

async def receive_messages(self):
    try:
        async for message in self.websocket:
            if isinstance(message, bytes):
                self.play_audio(message)
                self.update_statistics("speech", len(message))
            else:
                data = json.loads(message)
                if data['type'] == 'info':
                    self.log_message(data['message'])
                elif data['type'] == 'message':
                    self.log_message(f"{data['username']}: {data['message']}")
                elif data['type'] == 'room_update':
                    self.update_room_members(data['members'])
                elif data['type'] == 'room_list':
                    self.update_room_list(data)
                elif data['type'] == 'error':
                    self.log_message(f"Error: {data['message']}")
                elif data['type'] == 'talking':
                    self.update_talking_status(data['username'], data['status'])
                elif data['type'] == 'ping':
                    self.ping = data['ping']
                # Update statistics for different message types
                self.update_statistics(data['type'], len(message))
    except websockets.ConnectionClosed:
        self.log_message("Connection closed")

