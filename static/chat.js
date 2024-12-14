const ws = new WebSocket("ws://localhost:8888/websocket");

ws.onmessage = function (event) {
    try {
        const data = JSON.parse(event.data);

        if (data.type === "welcome") {
            displayChatMessage("Система", data.message);
        }

        if (data.type === "message") {
            const { sender, message } = data.data;
            displayChatMessage(sender, message);
        }

        if (data.type === "clients") {
            updateClientsList(data.clients);
        }
    } catch (error) {
        console.error("Ошибка при обработке входящего сообщения:", error, event.data);
    }
};

function displayChatMessage(sender, message) {
    const chat = document.getElementById("chat");
    const messageElement = document.createElement("div");
    messageElement.textContent = `${sender}: ${message}`;
    chat.appendChild(messageElement);

    // Автоматическая прокрутка вниз
    chat.scrollTop = chat.scrollHeight;
}

function updateClientsList(clients) {
    const clientsList = document.getElementById("clients");
    clientsList.innerHTML = "";

    clients.forEach((client) => {
        const clientItem = document.createElement("div");
        clientItem.textContent = client;
        clientsList.appendChild(clientItem);
    });
}

function sendMessage() {
    const input = document.getElementById("message");
    const message = input.value.trim();
    if (message) {
        ws.send(message);
        input.value = "";
        displayChatMessage("Вы", message); // Локальное отображение отправленного сообщения
    }
}
