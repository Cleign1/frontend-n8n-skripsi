document.addEventListener('DOMContentLoaded', function () {
    // Get the unique task ID from the data attribute on the body
    const taskId = document.body.dataset.taskId;
    const connectionStatus = document.getElementById('connection-status');
    
    if (!taskId) {
        console.error("Task ID is missing from the page.");
        connectionStatus.innerHTML = `
            <p class="font-bold">Error!</p>
            <p>Task ID tidak ditemukan. Halaman tidak dapat memuat pembaruan.</p>
        `;
        connectionStatus.className = 'mb-6 bg-red-100 border-l-4 border-red-500 text-red-700 p-4 rounded-md shadow-sm';
        return;
    }

    /**
     * Maps step statuses to their corresponding icon SVG markup.
     */
    const icons = {
        pending: `<svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>`,
        running: `<svg class="w-8 h-8 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>`,
        success: `<svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>`,
        fail: `<svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>`
    };

    /**
     * Maps step statuses to their corresponding Tailwind CSS classes for styling.
     */
    const statusStyles = {
        pending: {
            icon: 'border-gray-300 text-gray-500',
            title: 'text-gray-500',
            step: ''
        },
        running: {
            icon: 'border-blue-500 text-blue-500 animate-pulse',
            title: 'text-gray-800',
            step: 'running'
        },
        success: {
            icon: 'border-green-500 bg-green-500 text-white',
            title: 'text-gray-800',
            step: 'success'
        },
        fail: {
            icon: 'border-red-500 bg-red-500 text-white',
            title: 'text-red-500',
            step: 'fail'
        }
    };

    /**
     * Updates the visual state of a single timeline step.
     * @param {string} stepId - The unique ID of the step to update.
     * @param {string} status - The new status ('running', 'success', 'fail').
     * @param {string} [message] - An optional message to display.
     */
    function updateStepStatus(stepId, status, message) {
        const stepElement = document.querySelector(`.timeline-step[data-step-id="${stepId}"]`);
        if (!stepElement) {
            console.warn(`Step with ID ${stepId} not found in the DOM.`);
            return;
        }

        const iconContainer = stepElement.querySelector('.timeline-icon-container');
        const titleElement = stepElement.querySelector('.timeline-title');
        const statusMessage = stepElement.querySelector('.status-message');
        
        const styles = statusStyles[status] || statusStyles.pending;

        // Reset classes
        stepElement.classList.remove('running', 'success', 'fail');
        iconContainer.className = 'timeline-icon-container relative z-10 flex-shrink-0 flex items-center justify-center w-16 h-16 rounded-full border-4 bg-gray-50 transition-all duration-300 ease-in-out';
        titleElement.className = 'timeline-title text-lg font-semibold transition-colors duration-300';
        
        // Apply new classes
        if(styles.step) stepElement.classList.add(styles.step);
        iconContainer.classList.add(...styles.icon.split(' '));
        titleElement.classList.add(...styles.title.split(' '));

        // Update icon and message
        if (icons[status]) {
            iconContainer.innerHTML = icons[status];
        }
        statusMessage.textContent = message || (status.charAt(0).toUpperCase() + status.slice(1));
    }
    
    // --- WebSocket Connection Setup ---
    const socket = io({ transports: ['polling'] });

    socket.on('connect', () => {
        console.log('Successfully connected to WebSocket server.');
        connectionStatus.className = 'mb-6 bg-green-100 border-l-4 border-green-500 text-green-700 p-4 rounded-md shadow-sm';
        connectionStatus.innerHTML = `
            <p class="font-bold">Terhubung!</p>
            <p>Menunggu pembaruan status real-time.</p>
        `;
        socket.emit('join', { room: taskId });
    });

    socket.on('disconnect', () => {
        console.error('Disconnected from WebSocket server.');
        connectionStatus.className = 'mb-6 bg-red-100 border-l-4 border-red-500 text-red-700 p-4 rounded-md shadow-sm';
        connectionStatus.innerHTML = `
            <p class="font-bold">Koneksi Terputus!</p>
            <p>Tidak dapat menerima pembaruan. Silakan muat ulang halaman.</p>
        `;
    });

    socket.on('status_update', (data) => {
        console.log('Received status update:', data);
        updateStepStatus(data.step_id, data.status, data.message);

        if (data.status === 'fail') {
            updateStepStatus('workflow_finish', 'fail', 'Workflow gagal pada salah satu langkah.');
        }
        
        if (data.step_id === 'db9ca7f7-135d-4392-bf0a-36f1f688eb39' && data.status === 'success') {
            updateStepStatus('workflow_finish', 'success', 'Semua langkah berhasil diselesaikan.');
        }
    });
    
    window.addEventListener('beforeunload', () => {
        socket.emit('leave', { room: taskId });
    });
});
