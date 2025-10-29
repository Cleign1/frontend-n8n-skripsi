document.addEventListener('DOMContentLoaded', function () {
    const taskId = document.body.dataset.taskId;
    const connectionStatus = document.getElementById('connection-status');
    const backButton = document.getElementById('back-to-tasks');

    if (!taskId) {
        console.error("Task ID is missing from the page.");
        connectionStatus.innerHTML = `<p class="font-bold">Error!</p><p>Task ID tidak ditemukan.</p>`;
        connectionStatus.className = 'mb-6 bg-red-100 border-l-4 border-red-500 text-red-700 p-4';
        return;
    }

    if (backButton) {
        backButton.addEventListener('click', () => { window.location.href = '/tasks'; });
    }

    const icons = {
        pending: `<svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>`,
        running: `<svg class="w-8 h-8 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>`,
        success: `<svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>`,
        fail: `<svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>`
    };

    const statusStyles = {
        pending: { icon: 'border-gray-300 text-gray-500', title: 'text-gray-500', step: '' },
        running: { icon: 'border-blue-500 text-blue-500 animate-pulse', title: 'text-gray-800', step: 'running' },
        success: { icon: 'border-green-500 bg-green-500 text-white', title: 'text-gray-800', step: 'success' },
        fail: { icon: 'border-red-500 bg-red-500 text-white', title: 'text-red-500', step: 'fail' }
    };

    /**
     * Updates the visual state of a single timeline step.
     */
    function updateStepStatus(stepId, status, message) {
        // This function is now generic and works with 'data-step-id'
        const stepElement = document.querySelector(`.timeline-step[data-step-id="${stepId}"]`);
        if (!stepElement) {
            console.warn(`Step with ID ${stepId} not found in the DOM.`);
            return;
        }

        const iconContainer = stepElement.querySelector('.timeline-icon-container');
        const titleElement = stepElement.querySelector('.timeline-title');
        const statusMessageDiv = stepElement.querySelector('.status-message');
        const styles = statusStyles[status] || statusStyles.pending;

        stepElement.classList.remove('running', 'success', 'fail');
        iconContainer.className = 'timeline-icon-container relative z-10 flex-shrink-0 flex items-center justify-center w-16 h-16 rounded-full border-4 bg-gray-50 transition-all duration-300 ease-in-out';
        titleElement.className = 'timeline-title text-lg font-semibold transition-colors duration-300';
        
        if(styles.step) stepElement.classList.add(styles.step);
        iconContainer.classList.add(...styles.icon.split(' '));
        titleElement.classList.add(...styles.title.split(' '));

        if (icons[status]) {
            iconContainer.innerHTML = icons[status];
        }
        
        let finalMessage = message || (status.charAt(0).toUpperCase() + status.slice(1));
        try {
            const jsonOutput = JSON.parse(finalMessage.replace(/^Output: /, ''));
            finalMessage = `<pre class="text-xs bg-gray-100 p-2 rounded-md mt-2 whitespace-pre-wrap max-h-40 overflow-auto">${JSON.stringify(jsonOutput, null, 2)}</pre>`;
            statusMessageDiv.innerHTML = finalMessage;
        } catch (e) {
            statusMessageDiv.innerHTML = `<p>${finalMessage}</p>`;
        }
    }

    /**
     * Loads the saved state from the server and applies it to the timeline.
     */
    function applyInitialState() {
        // 'initialWorkflowState' is a global variable injected by the template
        if (typeof initialWorkflowState !== 'undefined' && initialWorkflowState) {
            console.log("Applying initial saved state:", initialWorkflowState);
            for (const stepId in initialWorkflowState) {
                const stepData = initialWorkflowState[stepId];
                updateStepStatus(stepId, stepData.status, stepData.message);
            }
        }
    }

    // --- APPLY THE SAVED STATE ON PAGE LOAD ---
    applyInitialState();
    
    // --- WebSocket Connection Setup ---
    // Force WebSocket-only to avoid session invalidation across workers
    const socket = io({
        transports: ['websocket'],
        upgrade: false,
        pingInterval: 25000,
        pingTimeout: 20000,
    });

    socket.on('connect', () => {
        console.log('Successfully connected to WebSocket server.');
        connectionStatus.innerHTML = `<p class="font-bold">Terhubung!</p><p>Mendengarkan pembaruan status real-time.</p>`;
        connectionStatus.className = 'mb-6 bg-green-100 border-l-4 border-green-500 text-green-700 p-4';
        socket.emit('join', { room: taskId });
    });

    socket.on('disconnect', () => {
        console.error('Disconnected from WebSocket server.');
        connectionStatus.innerHTML = `<p class="font-bold">Koneksi Terputus!</p><p>Tidak dapat menerima pembaruan.</p>`;
        connectionStatus.className = 'mb-6 bg-red-100 border-l-4 border-red-500 text-red-700 p-4';
    });

    // --- REAL-TIME UPDATE HANDLER ---
    socket.on('status_update', (data) => {
        console.log('Received real-time status update:', data);
        updateStepStatus(data.step_id, data.status, data.message);

        // Find the last step defined in the HTML to determine when the workflow is "finished"
        const allSteps = Array.from(document.querySelectorAll('.timeline-step:not([data-step-id="workflow_finish"])'));
        const lastDefinedStepId = allSteps.length > 0 ? allSteps[allSteps.length - 1].dataset.stepId : null;

        if (data.status === 'fail') {
            updateStepStatus('workflow_finish', 'fail', 'Workflow gagal pada salah satu langkah.');
        } else if (data.step_id === lastDefinedStepId && data.status === 'success') {
            updateStepStatus('workflow_finish', 'success', 'Semua langkah berhasil diselesaikan.');
        }
    });
    
    window.addEventListener('beforeunload', () => {
        socket.emit('leave', { room: taskId });
    });
});