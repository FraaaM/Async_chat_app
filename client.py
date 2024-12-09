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


async def listen_to_server(reader, chat_area, user_list):
    """Постоянно получает сообщения от сервера."""
    while True:
        message = await reader.read(100)
        if not message:
            break

        decoded_message = message.decode()
        if decoded_message.startswith("Users in"):
            user_list.config(state=tk.NORMAL)
            user_list.delete(1.0, tk.END)
            user_list.insert(tk.END, decoded_message + '\n')
            user_list.config(state=tk.DISABLED)
        else:
            chat_area.insert(tk.END, f"{decoded_message}\n")
            chat_area.see(tk.END)


async def send_message(writer, content):
    """Отправляет текстовое сообщение серверу."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    formatted_message = f"{nickname}({timestamp}): {content}"
    writer.write((formatted_message + '\n').encode())
    await writer.drain()


async def share_file(writer, filepath):
    """Отправляет файл на сервер."""
    writer.write(f"FILE:{os.path.basename(filepath)}\n".encode())
    await writer.drain()

    file_size = os.path.getsize(filepath)
    writer.write(f"{file_size}\n".encode())
    await writer.drain()

    with open(filepath, 'rb') as file:
        while chunk := file.read(1024):
            writer.write(chunk)
            await writer.drain()

    writer.write(f"File {os.path.basename(filepath)} sent successfully.\n".encode())
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
    asyncio.create_task(listen_to_server(connection_reader, chat_display, active_users_display))


def start_chat(ip, user_name, room_name):
    """Начинает чат, подключая клиента к серверу."""
    asyncio.run_coroutine_threadsafe(initialize_client(ip, user_name, room_name), event_loop)
    main_window.deiconify()


async def disconnect():
    """Отключает клиента от сервера."""
    global connection_writer
    if connection_writer:
        connection_writer.close()
        await connection_writer.wait_closed()
        main_window.destroy()


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
main_window.geometry("800x450")
main_window.title("Async Chat Client")
main_window.withdraw()

chat_frame = tk.Frame(main_window)
chat_frame.pack(fill="both", expand=True)

# Active users display
user_list_frame = tk.LabelFrame(chat_frame, text="Active Users")
user_list_frame.pack(fill="x")
active_users_display = tk.Text(user_list_frame, state=tk.DISABLED, height=1, wrap=tk.WORD, bg="#f9f9f9")
active_users_display.pack(fill="x")

# Chat display
chat_display_frame = tk.LabelFrame(chat_frame, text="Chat")
chat_display_frame.pack(fill="both", expand=True)
chat_display = scrolledtext.ScrolledText(chat_display_frame, wrap=tk.WORD)
chat_display.pack(fill="both", expand=True)

# Input area
input_frame = tk.Frame(chat_frame)
input_frame.pack(fill="x")

input_box = tk.Entry(input_frame)
input_box.pack(side="left", fill="x", expand=True)
input_box.bind("<Return>", lambda event: send_text())

send_button = tk.Button(input_frame, text="Send", command=send_text, bg="#4CAF50", fg="white")
send_button.pack(side="right", padx=5)

file_button = tk.Button(input_frame, text="Send File", command=send_file, bg="#2196F3", fg="white")
file_button.pack(side="right", padx=5)

disconnect_button = tk.Button(chat_frame, text="Disconnect", command=exit_chat, bg="#ff4d4d", fg="white")
disconnect_button.pack(side="bottom", pady=10)

# Connection dialog
def show_connection_window():
    dialog = tk.Toplevel(main_window)
    dialog.title("Connect to Chat Server")

    tk.Label(dialog, text="Server IP:").pack(pady=5)
    ip_entry = tk.Entry(dialog)
    ip_entry.insert(0, "127.0.0.1")
    ip_entry.pack()

    tk.Label(dialog, text="Username:").pack(pady=5)
    name_entry = tk.Entry(dialog)
    name_entry.pack()

    tk.Label(dialog, text="Chatroom:").pack(pady=5)
    room_entry = tk.Entry(dialog)
    room_entry.pack()

    def connect():
        global nickname
        ip = ip_entry.get()
        name = name_entry.get()
        room = room_entry.get()
        if ip and name and room:
            nickname = name
            start_chat(ip, name, room)
            dialog.destroy()

    connect_button = tk.Button(dialog, text="Connect", command=connect, bg="#4CAF50", fg="white")
    connect_button.pack(pady=10)

show_connection_window()

threading.Thread(target=setup_event_loop, daemon=True).start()

main_window.protocol("WM_DELETE_WINDOW", lambda: asyncio.run_coroutine_threadsafe(disconnect(), event_loop))
main_window.mainloop()
