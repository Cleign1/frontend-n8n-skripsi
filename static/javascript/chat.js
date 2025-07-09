document.addEventListener('DOMContentLoaded', () => {
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const chatMessages = document.getElementById('chat-messages');

    sendButton.addEventListener('click', sendMessage);
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    function sendMessage() {
        const message = messageInput.value.trim();
        if (message === '') return;

        appendMessage('user', message);
        messageInput.value = '';

        // Send message to the server and get the response
        fetch('/chat/send', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message }),
        })
        .then(response => response.json())
        .then(data => {
            appendMessage('agent', data.response);
        })
        .catch(error => {
            console.error('Error:', error);
            appendMessage('agent', 'Sorry, something went wrong.');
        });
    }

    function appendMessage(sender, message) {
        const messageElement = document.createElement('div');
        const messageBubble = document.createElement('div');

        if (sender === 'user') {
            messageElement.classList.add('flex', 'justify-end', 'mb-4');
            messageBubble.classList.add('bg-blue-500', 'text-white', 'rounded-lg', 'py-2', 'px-4', 'max-w-xs');
        } else {
            messageElement.classList.add('flex', 'justify-start', 'mb-4');
            messageBubble.classList.add('bg-gray-200', 'text-gray-800', 'rounded-lg', 'py-2', 'px-4', 'max-w-xs');
        }

        messageBubble.innerText = message;
        messageElement.appendChild(messageBubble);
        chatMessages.appendChild(messageElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
});
