import asyncio

connected_clients = {}
clients_mutex = asyncio.Lock()
chatrooms = set()


async def client_handler(reader, writer):
    client_address = writer.get_extra_info('peername')
    print(f"Connection established: {client_address}")

    try:
        user_name = (await reader.readline()).decode().strip()
        room_name = (await reader.readline()).decode().strip()

        async with clients_mutex:
            if room_name not in connected_clients:
                connected_clients[room_name] = []
            connected_clients[room_name].append((user_name, writer))
            chatrooms.add(room_name)

            print(f"{user_name} joined {room_name} from {client_address}")
            await notify_rooms()
            await notify_users_in_room(room_name)
            await broadcast_message(room_name, f"{user_name} has entered the room.")

        while True:
            received_data = await reader.readline()
            if not received_data:
                break

            content = received_data.decode().strip()
            if content.startswith("FILE:"):
                await handle_file_transfer(reader, content[5:], user_name, room_name)
            else:
                print(f"Message from {user_name} ({client_address}) in {room_name}: {content}")
                await broadcast_message(room_name, content)
    except Exception as error:
        print(f"Error with client {user_name}: {error}")
    finally:
        async with clients_mutex:
            if room_name in connected_clients:
                connected_clients[room_name] = [
                    client for client in connected_clients[room_name] if client[1] != writer
                ]
                if not connected_clients[room_name]:
                    del connected_clients[room_name]
                    chatrooms.remove(room_name)
                await notify_rooms()
                await notify_users_in_room(room_name)

        print(f"{user_name} disconnected from {room_name}")
        await broadcast_message(room_name, f"{user_name} has left the room.")
        writer.close()
        await writer.wait_closed()


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


async def notify_users_in_room(room):
    if room in connected_clients:
        active_users = [client[0] for client in connected_clients[room]]
        notification = f"Users in {room}: {', '.join(active_users)}\n"
        for _, writer in connected_clients[room]:
            writer.write(notification.encode())
            await writer.drain()


async def notify_rooms():
    room_list = f"Rooms: {', '.join(chatrooms)}\n"
    for room in connected_clients.values():
        for _, writer in room:
            writer.write(room_list.encode())
            await writer.drain()


async def broadcast_message(room, message):
    if room in connected_clients:
        for _, writer in connected_clients[room]:
            writer.write(f"{message}\n".encode())
            await writer.drain()


async def start_server():
    server_instance = await asyncio.start_server(client_handler, '127.0.0.1', 8888)
    server_address = server_instance.sockets[0].getsockname()
    print(f"Server running at {server_address}")
    async with server_instance:
        await server_instance.serve_forever()


asyncio.run(start_server())
