import json
import threading
import asyncio
import uuid
import os

from dotenv import load_dotenv
import tornado.ioloop
import tornado.web
import tornado.websocket
import redis

load_dotenv()

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


class WebSocketHandler(tornado.websocket.WebSocketHandler):
    """
    Класс WebSocketHandler обрабатывает подключения WebSocket, сообщения и отключения.
    Управляет подключениями клиентов, взаимодействует с Redis и транслирует сообщения всем подключенным клиентам.
    """

    clients = set()

    def open(self):
        """
        Вызывается при установке нового WebSocket-соединения.
        Присваивает пользователю имя, добавляет его в список онлайн-клиентов и отправляет приветственное сообщение.
        """
        self.username = self.get_argument("username", None)
        if not self.username:
            self.username = f"User-{str(uuid.uuid4())[:8]}"

        self.clients.add(self)
        redis_client.sadd("online_clients", self.username)

        self.update_clients_list()

        self.write_message(
            json.dumps(
                {
                    "type": "welcome",
                    "message": f"Добро пожаловать в чат, {self.username}!",
                }
            )
        )

    def on_message(self, message):
        """
        Вызывается при получении сообщения от клиента через WebSocket.
        Публикует сообщение в канал Redis `chat_channel`.

        Args:
            message (str): Сообщение, отправленное клиентом.
        """
        data = {
            "type": "message",
            "data": {"sender": self.username, "message": message},
        }
        redis_client.publish("chat_channel", json.dumps(data))

    def on_close(self):
        """
        Вызывается при закрытии WebSocket-соединения.
        Удаляет пользователя из списка онлайн-клиентов и обновляет список для всех подключенных клиентов.
        """
        self.clients.remove(self)
        redis_client.srem("online_clients", self.username)

        self.update_clients_list()

    def check_origin(self, origin):
        """
        Переопределяет проверку источника (origin) для разрешения кросс-доменных WebSocket-соединений.

        Args:
            origin (str): Источник WebSocket-соединения.

        Returns:
            bool: Всегда возвращает True.
        """
        return True

    def update_clients_list(self):
        """
        Обновляет список онлайн-клиентов и транслирует обновленный список всем подключенным клиентам.
        """
        online_clients = list(redis_client.smembers("online_clients"))

        data = {"type": "clients", "clients": online_clients}

        for client in self.clients:
            client.write_message(json.dumps(data))


async def redis_listener():
    """
    Слушает сообщения, публикуемые в канале Redis `chat_channel`, и транслирует их всем WebSocket-клиентам.
    """
    pubsub = redis_client.pubsub()
    pubsub.subscribe("chat_channel")
    for message in pubsub.listen():
        if message["type"] == "message":
            data = json.loads(message["data"])
            for client in WebSocketHandler.clients:
                client.write_message(json.dumps(data))


def start_redis_listener():
    """
    Запускает слушатель Redis в новом цикле событий asyncio, чтобы избежать блокировки цикла ввода-вывода Tornado.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(redis_listener())


if __name__ == "__main__":
    """
    Точка входа в приложение Tornado.
    Инициализирует WebSocket-сервер, обслуживает статические файлы и запускает цикл обработки событий.
    """
    app = tornado.web.Application(
        [
            (r"/websocket", WebSocketHandler),
            (
                r"/(.*)",
                tornado.web.StaticFileHandler,
                {"path": "./static", "default_filename": "index.html"},
            ),
        ]
    )
    app.listen(8888)

    print("Сервер запущен: http://localhost:8888")
    threading.Thread(target=start_redis_listener, daemon=True).start()

    tornado.ioloop.IOLoop.current().start()
