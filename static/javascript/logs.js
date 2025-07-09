// static/javascript/logs.js
document.addEventListener('DOMContentLoaded', () => {
    const logModal = document.getElementById('log-modal');
    const logModalTitle = document.getElementById('log-modal-title');
    const logContainer = document.getElementById('log-container');
    const showTaskLogsBtn = document.getElementById('show-task-logs-btn');
    const showServerLogsBtn = document.getElementById('show-server-logs-btn');
    const closeLogModalBtn = document.getElementById('close-log-modal-btn');

    let currentLogFilter = null; // 'task' or 'server'

    // --- WebSocket Connection ---
    const socket = io({ transports: ['polling'] });

    socket.on('connect', () => {
        console.log('Connected to server via WebSocket.');
    });

    socket.on('log_message', (msg) => {
        // Only display logs if the modal is open
        if (logModal.classList.contains('hidden')) {
            return;
        }

        const isServerLog = msg.logger_name && msg.logger_name.includes('werkzeug');

        let shouldDisplay = false;
        if (currentLogFilter === 'server' && isServerLog) {
            shouldDisplay = true;
        } else if (currentLogFilter === 'task' && !isServerLog) {
            shouldDisplay = true;
        }

        // Filter based on which button was clicked
        if (shouldDisplay) {
            const logElement = document.createElement('div');
            logElement.textContent = msg.data;

            if (msg.data.includes('WARNING')) {
                logElement.classList.add('text-yellow-400');
            } else if (msg.data.includes('ERROR') || msg.data.includes('CRITICAL')) {
                logElement.classList.add('text-red-500');
            } else if (msg.data.includes('INFO')) {
                 logElement.classList.add('text-green-400');
            }

            logContainer.appendChild(logElement);
            logContainer.parentElement.scrollTop = logContainer.parentElement.scrollHeight;
        }
    });

    // --- Modal Control ---
    const openModal = (filter, title) => {
        currentLogFilter = filter;
        logModalTitle.textContent = title;
        logContainer.innerHTML = ''; // Clear previous logs
        logModal.classList.remove('hidden');
    };

    const closeModal = () => {
        logModal.classList.add('hidden');
        currentLogFilter = null; // Stop listening
    };

    showTaskLogsBtn.addEventListener('click', () => openModal('task', 'Live Celery Worker Logs'));
    showServerLogsBtn.addEventListener('click', () => openModal('server', 'Live Flask Server Logs'));
    closeLogModalBtn.addEventListener('click', closeModal);
    logModal.addEventListener('click', (event) => {
        if (event.target === logModal) {
            closeModal();
        }
    });
});
