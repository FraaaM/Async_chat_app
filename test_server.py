import pytest
import asyncio
from unittest.mock import AsyncMock, Mock
from server import client_handler, broadcast_message, notify_users_in_room, handle_file_transfer, connected_clients, clients_mutex

#pytest test_server.py

# Мок для writer
@pytest.fixture
def mock_writer():
    mock = Mock()
    mock.write = AsyncMock()
    mock.drain = AsyncMock()
    mock.get_extra_info = Mock(return_value=("127.0.0.1", 8888))
    return mock


# Мок для reader
@pytest.fixture
def mock_reader():
    return AsyncMock()


# Тестирование обработки подключения клиента
@pytest.mark.asyncio
async def test_client_handler(mock_reader, mock_writer):
    """Тестируем обработку подключения клиента."""
    # Подготовка
    mock_reader.readline = AsyncMock(side_effect=[b"user1\n", b"room1\n", b""])
    
    # Создаем пустой список клиентов в комнате
    connected_clients.clear()

    # Вызов функции
    await client_handler(mock_reader, mock_writer)

    # Проверяем, что пользователь был добавлен в список клиентов комнаты
    async with clients_mutex:
        assert "room1" in connected_clients
        assert len(connected_clients["room1"]) == 1
        assert connected_clients["room1"][0][0] == "user1"

    # Проверяем, что сообщение о входе в комнату было отправлено
    mock_writer.write.assert_any_call(b"user1 has entered the room.\n")
    await mock_writer.drain.assert_awaited()


# Тестирование отправки сообщений в комнату
@pytest.mark.asyncio
async def test_broadcast_message(mock_writer):
    """Тестируем отправку сообщений в комнату."""
    # Подготовка состояния
    connected_clients["room1"] = [("user1", mock_writer)]

    # Вызов функции
    await broadcast_message("room1", "Hello, room!")

    # Проверяем, что сообщение отправлено
    mock_writer.write.assert_called_with(b"Hello, room!\n")
    await mock_writer.drain.assert_awaited()


# Тестирование уведомлений о пользователях в комнате
@pytest.mark.asyncio
async def test_notify_users_in_room(mock_writer):
    """Тестируем уведомления пользователей в комнате."""
    # Подготовка состояния
    connected_clients["room1"] = [("user1", mock_writer), ("user2", mock_writer)]

    # Вызов функции
    await notify_users_in_room("room1")

    # Проверяем, что уведомление о пользователях отправлено
    expected_message = "Users in room1: user1, user2\n".encode()
    mock_writer.write.assert_called_with(expected_message)
    await mock_writer.drain.assert_awaited()


# Тестирование обработки передачи файла
@pytest.mark.asyncio
async def test_handle_file_transfer(mock_reader, mock_writer):
    """Тестируем обработку передачи файла."""
    # Подготовка
    mock_reader.readline = AsyncMock(side_effect=[b"5\n"])  # Размер файла
    mock_reader.read = AsyncMock(return_value=b"file content")  # Содержимое файла

    # Вызов функции
    await handle_file_transfer(mock_reader, "testfile.txt", "user1", "room1")

    # Проверяем, что сообщение о передаче файла было отправлено
    mock_writer.write.assert_any_call(b"user1 is sharing a file: testfile.txt\n")
    await mock_writer.drain.assert_awaited()
    mock_writer.write.assert_any_call(b"File upload complete: testfile.txt\n")
    await mock_writer.drain.assert_awaited()


# Дополнительные тесты на закрытие подключения клиента
@pytest.mark.asyncio
async def test_client_disconnect(mock_reader, mock_writer):
    """Тестируем отключение клиента."""
    mock_reader.readline = AsyncMock(side_effect=[b"user1\n", b"room1\n", b""])

    # Подготовка состояния
    connected_clients["room1"] = [("user1", mock_writer)]

    # Вызов функции
    await client_handler(mock_reader, mock_writer)

    # Проверяем, что сообщение о выходе клиента из комнаты отправлено
    mock_writer.write.assert_any_call(b"user1 has left the room.\n")
    await mock_writer.drain.assert_awaited()

    # Проверяем, что клиента больше нет в списке
    async with clients_mutex:
        assert len(connected_clients["room1"]) == 0


# Запуск тестов
if __name__ == "__main__":
    pytest.main()
