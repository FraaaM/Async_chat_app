import asyncio

clients_mutex = asyncio.Lock()
chatrooms = set()
connected_clients = {}  # Словарь, где ключ - название комнаты, значение - список пользователей
all_users = set()  # Для всех пользователей в системе

async def client_handler(reader, writer):
    client_address = writer.get_extra_info('peername')
    user_name = None
    room_name = None
    try:
        user_name = (await reader.readline()).decode().strip()
        room_name = (await reader.readline()).decode().strip()

        async with clients_mutex:
            if room_name not in connected_clients:
                connected_clients[room_name] = []
            connected_clients[room_name].append((user_name, writer))
            chatrooms.add(room_name)
            all_users.add(user_name)

        await notify_rooms()
        await notify_users_in_room(room_name)

        await broadcast_message(room_name, f"{user_name} has joined the room.")

        while True:
            received_data = await reader.readline()
            if not received_data:
                break
            content = received_data.decode().strip()
            if content.startswith("FILE:"):
                await handle_file_transfer(reader, content[5:], user_name, room_name)
            else:
                await broadcast_message(room_name, f"{user_name}: {content}")
    except Exception as e:
        print(f"Error with client {client_address}: {e}")
    finally:
        async with clients_mutex:
            if user_name and room_name:
                if room_name in connected_clients:
                    connected_clients[room_name] = [
                        client for client in connected_clients[room_name] if client[0] != user_name
                    ]
                    if not connected_clients[room_name]:
                        del connected_clients[room_name]
                        chatrooms.remove(room_name)
                all_users.discard(user_name)

        await notify_rooms()
        await notify_users_in_room(room_name)
        await broadcast_message(room_name, f"{user_name} has left the room.")

        writer.close()
        await writer.wait_closed()

async def notify_users_in_room(room_name):
    """Notify users in a specific room about the current users in the room."""
    if room_name in connected_clients:
        users_in_room = ', '.join([user for user, _ in connected_clients[room_name]])
        user_list = f"Users: {users_in_room}\n"
        for _, writer in connected_clients[room_name]:
            writer.write(user_list.encode())
            await writer.drain()

async def notify_rooms():
    """Notify all clients about the list of all chatrooms."""
    room_list = f"Rooms: {', '.join(chatrooms)}\n"
    async with clients_mutex:
        for room_clients in connected_clients.values():
            for _, writer in room_clients:
                writer.write(room_list.encode())
                await writer.drain()

async def broadcast_message(room, message):
    """Broadcast a message to all users in a specific room."""
    async with clients_mutex:
        if room in connected_clients:
            for _, writer in connected_clients[room]:
                writer.write(f"{message}\n".encode())
                await writer.drain()

async def handle_file_transfer(reader, filename, sender_name, room):
    await broadcast_message(room, f"{sender_name} is sharing a file: {filename}")
    file_size_data = await reader.readline()
    try:
        file_size = int(file_size_data.decode().strip())
    except ValueError:
        print(f"Invalid file size from {sender_name}.")
        return

    with open(filename, 'wb') as file:
        bytes_written = 0
        while bytes_written < file_size:
            chunk = await reader.read(1024)
            if not chunk:
                break
            file.write(chunk)
            bytes_written += len(chunk)

    await broadcast_message(room, f"File upload complete: {filename}")

async def start_server():
    server = await asyncio.start_server(client_handler, '127.0.0.1', 8888)
    print(f"Server started on {server.sockets[0].getsockname()}")
    async with server:
        await server.serve_forever()

asyncio.run(start_server())
