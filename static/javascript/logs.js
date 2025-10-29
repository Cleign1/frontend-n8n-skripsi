// static/javascript/logs.js
document.addEventListener('DOMContentLoaded', () => {
    const logModal = document.getElementById('log-modal');
    const logModalTitle = document.getElementById('log-modal-title');
    const logContainer = document.getElementById('log-container');
    const showTaskLogsBtn = document.getElementById('show-task-logs-btn');
    const showServerLogsBtn = document.getElementById('show-server-logs-btn');
    const closeLogModalBtn = document.getElementById('close-log-modal-btn');

    let currentLogFilter = null; // 'task' or 'server'
    let logBuffer = [];
    let logUpdateInterval = null;

    /**
     * Processes the log buffer and updates the DOM with new messages.
     */
    function renderLogs() {
        if (logBuffer.length === 0) {
            return;
        }

        const fragment = document.createDocumentFragment();
        // Take all logs currently in the buffer to render them.
        const logsToRender = logBuffer.splice(0, logBuffer.length);

        logsToRender.forEach(msg => {
            const isServerLog = msg.logger_name && msg.logger_name.includes('werkzeug');

            let shouldDisplay = false;
            if (currentLogFilter === 'server' && isServerLog) {
                shouldDisplay = true;
            } else if (currentLogFilter === 'task' && !isServerLog) {
                shouldDisplay = true;
            }

            if (shouldDisplay) {
                const logElement = document.createElement('div');
                logElement.textContent = msg.data;

                // Apply colors based on log level
                if (msg.data.includes('WARNING')) {
                    logElement.classList.add('text-yellow-400');
                } else if (msg.data.includes('ERROR') || msg.data.includes('CRITICAL')) {
                    logElement.classList.add('text-red-500');
                } else if (msg.data.includes('INFO')) {
                    logElement.classList.add('text-green-400');
                }
                fragment.appendChild(logElement);
            }
        });

        // Append the entire batch of new logs at once
        if (fragment.hasChildNodes()) {
            logContainer.appendChild(fragment);
            // Auto-scroll to the bottom
            logContainer.parentElement.scrollTop = logContainer.parentElement.scrollHeight;
        }
    }

    // --- WebSocket Connection ---
    // Force pure WebSocket transport to avoid sticky-session issues across multiple workers
    const socket = io({
        transports: ['websocket'],
        upgrade: false,
        pingInterval: 25000,
        pingTimeout: 20000,
    });

    socket.on('connect', () => {
        console.log('Connected to server via WebSocket.');
    });

    socket.on('log_message', (msg) => {
        // Instead of rendering immediately, add the message to the buffer.
        logBuffer.push(msg);
    });

    // --- Modal Control ---
    const openModal = (filter, title) => {
        currentLogFilter = filter;
        logModalTitle.textContent = title;
        logContainer.innerHTML = ''; // Clear previous logs
        logBuffer = []; // Clear the buffer as well
        logModal.classList.remove('hidden');

        // Start a timer to render logs from the buffer every 1.5 seconds.
        if (!logUpdateInterval) {
            logUpdateInterval = setInterval(renderLogs, 1500);
        }
    };

    const closeModal = () => {
        logModal.classList.add('hidden');
        currentLogFilter = null;
        
        // Stop the timer when the modal is closed to save resources.
        if (logUpdateInterval) {
            clearInterval(logUpdateInterval);
            logUpdateInterval = null;
        }
    };

    showTaskLogsBtn.addEventListener('click', () => openModal('task', 'Log Pekerja Celery Secara Langsung'));
    showServerLogsBtn.addEventListener('click', () => openModal('server', 'Log Server Flask Secara Langsung'));
    closeLogModalBtn.addEventListener('click', closeModal);
    logModal.addEventListener('click', (event) => {
        if (event.target === logModal) {
            closeModal();
        }
    });
});