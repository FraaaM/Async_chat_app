import asyncio
import threading
import tkinter as tk
from tkinter import filedialog, scrolledtext
from datetime import datetime
import os

event_loop = None
connection_reader = None
connection_writer = None
nickname = None
chatrooms = []  # Список всех комнат
users = []  # Список всех пользователей
chat_history = {} 

async def listen_to_server(reader, chat_area, user_list, room_list):
    """Receive messages from the server and update UI."""
    while True:
        message = await reader.read(1024) 
        if not message:
            break

        decoded_message = message.decode().strip()
        if decoded_message.startswith("Users:"):
            users = decoded_message[7:].strip()
            user_list.config(state=tk.NORMAL)
            user_list.delete(1.0, tk.END)
            user_list.insert(tk.END, users + '\n')
            user_list.config(state=tk.DISABLED)
        elif decoded_message.startswith("Rooms:"):
            rooms = decoded_message[7:].strip()
            room_list.config(state=tk.NORMAL)
            room_list.delete(1.0, tk.END)
            room_list.insert(tk.END, rooms + '\n')
            room_list.config(state=tk.DISABLED)
        else:
            current_room_name = room_list.get("1.0", tk.END).strip().split("\n")[0]  # Первая комната как текущая
            chat_area.insert(tk.END, f"[{current_room_name}] {decoded_message}\n")
            chat_area.see(tk.END)


async def send_message(writer, content):
    """Отправляет текстовое сообщение серверу."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    formatted_message = f"{nickname}({timestamp}): {content}"
    writer.write((formatted_message + '\n').encode())
    await writer.drain()


def send_text():
    """Обработчик кнопки отправки сообщения."""
    text = input_box.get()
    input_box.delete(0, tk.END)
    asyncio.run_coroutine_threadsafe(send_message(connection_writer, text), event_loop)


def send_file():
    """Обработчик кнопки отправки файла."""
    file_path = filedialog.askopenfilename()
    if file_path:
        asyncio.run_coroutine_threadsafe(share_file(connection_writer, file_path), event_loop)


async def initialize_client(ip, name, chatroom):
    """Подключается к серверу и регистрирует клиента."""
    global connection_reader, connection_writer
    connection_reader, connection_writer = await asyncio.open_connection(ip, 8888)
    connection_writer.write(f"{name}\n{chatroom}\n".encode())
    await connection_writer.drain()
    asyncio.create_task(listen_to_server(connection_reader, chat_display, active_users_display, chatrooms_display))


def start_chat(ip, user_name, room_name):
    """Начинает чат, подключая клиента к серверу."""
    current_room.set(room_name)
    if room_name in chat_history:
        chat_display.delete(1.0, tk.END)
        chat_display.insert(tk.END, "\n".join(chat_history[room_name]) + "\n")
    else:
        chat_display.delete(1.0, tk.END)

    asyncio.run_coroutine_threadsafe(initialize_client(ip, user_name, room_name), event_loop)
    main_window.deiconify()
    connection_window.withdraw()


async def disconnect():
    """Отключает клиента от сервера."""
    global connection_writer
    if connection_writer:
        connection_writer.close()
        await connection_writer.wait_closed()
        connection_writer = None
    main_window.withdraw()
    connection_window.deiconify()


def exit_chat():
    """Обработчик кнопки отключения."""
    asyncio.run_coroutine_threadsafe(disconnect(), event_loop)


def setup_event_loop():
    """Запускает асинхронный цикл в отдельном потоке."""
    global event_loop
    event_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(event_loop)
    event_loop.run_forever()


# GUI
main_window = tk.Tk()
main_window.geometry("800x600")
main_window.title("Async Chat Client")
main_window.withdraw()

chat_frame = tk.Frame(main_window)
chat_frame.pack(fill="both", expand=True)

# Верхняя часть с активными пользователями и комнатами
top_frame = tk.Frame(chat_frame)
top_frame.pack(fill="x", padx=5, pady=5)

# Active users display
user_list_frame = tk.LabelFrame(top_frame, text="Active Users", width=200)
user_list_frame.pack(side="left", fill="y", padx=5, pady=5)
active_users_display = scrolledtext.ScrolledText(user_list_frame, state=tk.DISABLED, height=10, wrap=tk.WORD, bg="#f9f9f9")
active_users_display.pack(fill="both", expand=True)

# Chatrooms display
rooms_frame = tk.LabelFrame(top_frame, text="Chatrooms", width=200)
rooms_frame.pack(side="right", fill="y", padx=5, pady=5)
chatrooms_display = scrolledtext.ScrolledText(rooms_frame, wrap=tk.WORD, state=tk.DISABLED, height=10, bg="#f9f9f9")
chatrooms_display.pack(fill="both", expand=True)

chat_display_frame = tk.LabelFrame(chat_frame, text="Chat")
chat_display_frame.pack(fill="both", expand=True, padx=5, pady=5)
chat_display = scrolledtext.ScrolledText(chat_display_frame, wrap=tk.WORD, state=tk.NORMAL, bg="#ffffff")
chat_display.pack(fill="both", expand=True)

input_frame = tk.Frame(chat_frame)
input_frame.pack(fill="x", padx=5, pady=5)

input_box = tk.Entry(input_frame)
input_box.pack(side="left", fill="x", expand=True)
input_box.bind("<Return>", lambda event: send_text())

disconnect_button = tk.Button(input_frame, text="Disconnect", command=exit_chat, bg="#ff4d4d", fg="white")
disconnect_button.pack(side="right", padx=5)

file_button = tk.Button(input_frame, text="Send File", command=send_file, bg="#2196F3", fg="white")
file_button.pack(side="right", padx=5)

send_button = tk.Button(input_frame, text="Send", command=send_text, bg="#4CAF50", fg="white")
send_button.pack(side="right", padx=5)


# Connection dialog
connection_window = tk.Toplevel(main_window)
connection_window.title("Connect to Chat Server")

tk.Label(connection_window, text="Server IP:").pack(pady=5)
ip_entry = tk.Entry(connection_window)
ip_entry.insert(0, "127.0.0.1")
ip_entry.pack()

tk.Label(connection_window, text="Username:").pack(pady=5)
name_entry = tk.Entry(connection_window)
name_entry.pack()

tk.Label(connection_window, text="Chatroom:").pack(pady=5)
room_entry = tk.Entry(connection_window)
room_entry.pack()

current_room = tk.StringVar()


def connect():
    global nickname
    ip = ip_entry.get()
    name = name_entry.get()
    room = room_entry.get()
    if ip and name and room:
        nickname = name
        start_chat(ip, name, room)


connect_button = tk.Button(connection_window, text="Connect", command=connect, bg="#4CAF50", fg="white")
connect_button.pack(pady=10)

threading.Thread(target=setup_event_loop, daemon=True).start()

main_window.protocol("WM_DELETE_WINDOW", lambda: asyncio.run_coroutine_threadsafe(disconnect(), event_loop))
main_window.mainloop()
