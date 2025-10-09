document.addEventListener('DOMContentLoaded', function() {
    // --- UI Element Selection ---
    // Get references to all the HTML elements we'll be interacting with.
    const tasksContainer = document.getElementById('tasks-container');
    const emptyState = document.getElementById('empty-state');
    const refreshBtn = document.getElementById('refresh-btn');
    const clearCompletedBtn = document.getElementById('clear-completed-btn');
    
    // Modal elements for showing task details
    const taskDetailModal = document.getElementById('task-detail-modal');
    const modalTaskName = document.getElementById('modal-task-name');
    const modalTaskContent = document.getElementById('modal-task-content');
    const closeModalBtn = document.getElementById('close-modal-btn');
    const modalTerminateBtn = document.getElementById('modal-terminate-btn');
    const modalRemoveBtn = document.getElementById('modal-remove-btn');
    
    // --- State Variables ---
    let currentTaskId = null; // Stores the ID of the task currently being viewed in the modal
    let refreshInterval = null; // Holds the interval for auto-refreshing tasks

    // --- Configuration ---
    // Maps task statuses to specific Tailwind CSS classes for styling badges.
    const statusColors = {
        'PENDING': 'bg-yellow-100 text-yellow-800 border-yellow-200',
        'STARTED': 'bg-blue-100 text-blue-800 border-blue-200',
        'SUCCESS': 'bg-green-100 text-green-800 border-green-200',
        'FAILURE': 'bg-red-100 text-red-800 border-red-200',
        'RETRY': 'bg-orange-100 text-orange-800 border-orange-200',
        'REVOKED': 'bg-gray-100 text-gray-800 border-gray-200',
        'Sedang Prediksi': 'bg-purple-100 text-purple-800 border-purple-200',
        'Prediksi Selesai': 'bg-green-100 text-green-800 border-green-200'
    };

    // --- Helper Functions ---

    /**
     * Returns the appropriate CSS classes for a given task status.
     * @param {string} status - The status of the task (e.g., 'SUCCESS').
     * @returns {string} Tailwind CSS classes.
     */
    function getStatusColor(status) {
        return statusColors[status] || 'bg-gray-100 text-gray-800 border-gray-200';
    }

    /**
     * Formats an ISO date string into a more readable local format.
     * @param {string} isoString - The ISO date string from the server.
     * @returns {string} Formatted date string (e.g., "9/10/2025, 20:52") or 'N/A'.
     */
    function formatDateTime(isoString) {
        if (!isoString) return 'N/A';
        const date = new Date(isoString);
        return date.toLocaleString('id-ID', { year: 'numeric', month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    }

    /**
     * Generates the HTML for a single task card.
     * @param {object} task - The task object from the API.
     * @returns {string} The complete HTML string for the task card.
     */
    function createTaskCard(task) {
        const statusColor = getStatusColor(task.status);
        
        // --- Determine Task Type and State ---
        const isRunning = ['PENDING', 'STARTED', 'Sedang Prediksi', 'RETRY'].includes(task.status);
        const isPredictionTask = task.task_id && task.task_id.startsWith('prediksi_');
        const isWorkflowTask = task.task_id && task.task_id.startsWith('workflow_');

        // --- Simplified Button Logic ---
        // This block determines which action buttons to show based on the task type.
        let actionButtonsHtml = '';
        if (isWorkflowTask) {
            // Workflow tasks get a special "View Process" link.
            actionButtonsHtml = `
                <a href="/workflow/${task.task_id}" class="bg-cyan-600 hover:bg-cyan-700 text-white px-3 py-2 rounded-lg text-sm font-medium transition-colors shadow-sm">
                    Lihat Proses
                </a>
            `;
        } else {
            // All other tasks (Celery, Prediction) get a "Detail" button.
            actionButtonsHtml = `
                <button onclick="showTaskDetail('${task.task_id}')" class="bg-blue-600 hover:bg-blue-700 text-white px-3 py-2 rounded-lg text-sm font-medium transition-colors shadow-sm">
                    Detail
                </button>
            `;
        }

        // Add a second button for terminating or removing the task.
        if (isPredictionTask || isWorkflowTask) {
             // Prediction and Workflow tasks can always be removed from the list.
            actionButtonsHtml += `
                <button onclick="removeTask('${task.task_id}')" class="bg-gray-600 hover:bg-gray-700 text-white px-3 py-2 rounded-lg text-sm font-medium transition-colors shadow-sm">
                    Remove
                </button>
            `;
        } else { // It's a standard Celery task
            if (isRunning) {
                // If it's running, show the 'Terminate' button.
                actionButtonsHtml += `
                    <button onclick="abortTask('${task.task_id}')" class="bg-red-600 hover:bg-red-700 text-white px-3 py-2 rounded-lg text-sm font-medium transition-colors shadow-sm">
                        Terminate
                    </button>
                `;
            } else {
                // If it's finished (SUCCESS, FAILURE, etc.), show the 'Remove' button.
                actionButtonsHtml += `
                    <button onclick="removeTask('${task.task_id}')" class="bg-gray-600 hover:bg-gray-700 text-white px-3 py-2 rounded-lg text-sm font-medium transition-colors shadow-sm">
                        Remove
                    </button>
                `;
            }
        }


        // --- Card HTML Structure ---
        return `
            <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-md transition-all duration-200" data-task-id="${task.task_id}">
                <div class="flex items-start justify-between">
                    <div class="flex-1 pr-4">
                        <div class="flex items-center gap-3 mb-3">
                            <h3 class="text-lg font-semibold text-gray-900">${task.task_name || 'Unnamed Task'}</h3>
                            <span class="px-3 py-1 text-xs font-medium rounded-full border ${statusColor}">
                                ${task.status || 'UNKNOWN'}
                            </span>
                        </div>
                        
                        <div class="space-y-2 text-sm text-gray-600 mb-4">
                            <p><span class="font-medium text-gray-700">Task ID:</span> <code class="bg-gray-100 px-2 py-1 rounded text-xs">${task.task_id}</code></p>
                            <p><span class="font-medium text-gray-700">File:</span> ${task.filename || 'N/A'}</p>
                            <p><span class="font-medium text-gray-700">Created:</span> ${formatDateTime(task.created_at)}</p>
                            ${task.last_message ? `<p><span class="font-medium text-gray-700">Last Message:</span> <span class="text-gray-900">${task.last_message}</span></p>` : ''}
                        </div>
                        
                        ${isRunning && !isPredictionTask && !isWorkflowTask ? `
                            <div class="mb-4">
                                <div class="flex items-center justify-between text-sm mb-2">
                                    <span class="text-gray-600 font-medium">Progress</span>
                                    <span class="text-blue-700 font-medium flex items-center">
                                        <div class="w-2 h-2 bg-blue-500 rounded-full animate-pulse mr-2"></div>
                                        Running...
                                    </span>
                                </div>
                                <div class="w-full bg-gray-200 rounded-full h-2.5">
                                    <div class="bg-gradient-to-r from-blue-500 to-blue-600 h-2.5 rounded-full animate-pulse" style="width: 100%"></div>
                                </div>
                            </div>
                        ` : ''}
                    </div>
                    
                    <div class="flex flex-col sm:flex-row gap-2 ml-4">
                        ${actionButtonsHtml}
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Fetches the list of tasks from the API and renders them.
     */
    async function loadTasks() {
        try {
            const response = await fetch('/api/tasks');
            const tasks = await response.json();

            if (tasks.length === 0) {
                tasksContainer.innerHTML = '';
                emptyState.classList.remove('hidden');
            } else {
                emptyState.classList.add('hidden');
                // Sort tasks by creation date, newest first, for consistent display
                tasks.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
                tasksContainer.innerHTML = tasks.map(createTaskCard).join('');
            }
        } catch (error) {
            console.error('Error loading tasks:', error);
            tasksContainer.innerHTML = `<div class="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700"><p>Error loading tasks: ${error.message}</p></div>`;
        }
    }

    // --- Window-scoped Functions (for onclick handlers in HTML) ---

    /**
     * Shows the task detail modal.
     * @param {string} taskId - The ID of the task to show details for.
     */
    window.showTaskDetail = async function(taskId) {
        currentTaskId = taskId;

        try {
            const response = await fetch(`/api/tasks/${taskId}/status`);
            const task = await response.json();

            modalTaskName.textContent = task.task_name || `Task ${taskId}`;
            modalTaskContent.innerHTML = `
                <div class="space-y-4">
                    <div><label class="font-medium">Task ID:</label> <code class="bg-gray-100 p-1 rounded">${task.task_id}</code></div>
                    <div><label class="font-medium">Status:</label> <span class="px-2 py-1 text-xs font-medium rounded-full border ${getStatusColor(task.status)}">${task.status}</span></div>
                    <div><label class="font-medium">Filename:</label> ${task.filename || 'N/A'}</div>
                    <div><label class="font-medium">Created At:</label> ${formatDateTime(task.created_at)}</div>
                    ${task.last_message ? `<div><label class="font-medium">Last Message:</label> <p class="bg-gray-50 p-2 rounded">${task.last_message}</p></div>` : ''}
                    ${task.result ? `<div><label class="font-medium">Result:</label> <pre class="text-xs bg-gray-50 p-2 rounded max-h-40 overflow-auto">${task.result}</pre></div>` : ''}
                </div>
            `;

            // Simplified logic to show/hide buttons in the modal
            const isRunning = ['PENDING', 'STARTED', 'Sedang Prediksi', 'RETRY'].includes(task.status);
            const isPredictionTask = task.task_id && task.task_id.startsWith('prediksi_');

            modalTerminateBtn.style.display = isRunning && !isPredictionTask ? 'block' : 'none';
            modalRemoveBtn.style.display = !isRunning || isPredictionTask ? 'block' : 'none';

            taskDetailModal.classList.remove('hidden');

        } catch (error) {
            console.error('Error loading task detail:', error);
            alert('Error loading task detail: ' + error.message);
        }
    };

    /**
     * Sends a request to abort a running Celery task.
     * @param {string} taskId - The ID of the task to abort.
     */
    window.abortTask = async function(taskId) {
        if (!confirm(`Are you sure you want to abort task ${taskId}?`)) return;

        try {
            const response = await fetch(`/api/tasks/${taskId}/abort`, { method: 'POST' });
            const result = await response.json();
            alert(result.message || result.error);
            loadTasks(); // Refresh the list to show the 'REVOKED' status
        } catch (error) {
            alert('Error aborting task: ' + error.message);
        }
    };

    /**
     * Sends a request to remove a task from the Redis list (does not stop a running task).
     * @param {string} taskId - The ID of the task to remove.
     */
    window.removeTask = async function(taskId) {
        if (!confirm(`Are you sure you want to remove task ${taskId} from the list? This cannot be undone.`)) return;

        try {
            const response = await fetch(`/api/tasks/${taskId}/remove`, { method: 'DELETE' });
            const result = await response.json();

            if (response.ok) {
                loadTasks(); // Refresh the list
                if (currentTaskId === taskId) {
                    taskDetailModal.classList.add('hidden'); // Close modal if it was open for this task
                }
            } else {
                alert('Error: ' + result.error);
            }
        } catch (error) {
            alert('Error removing task: ' + error.message);
        }
    };

    // --- Event Listeners ---
    refreshBtn.addEventListener('click', loadTasks);

    clearCompletedBtn.addEventListener('click', async function() {
        if (!confirm('Are you sure you want to clear all completed, failed, and revoked tasks?')) return;

        try {
            const response = await fetch('/api/tasks');
            const tasks = await response.json();
            const completedTasks = tasks.filter(task => ['SUCCESS', 'FAILURE', 'REVOKED', 'Prediksi Selesai'].includes(task.status));

            // Send all delete requests in parallel for efficiency
            await Promise.all(completedTasks.map(task =>
                fetch(`/api/tasks/${task.task_id}/remove`, { method: 'DELETE' })
            ));

            loadTasks(); // Refresh the list after clearing
        } catch (error) {
            alert('Error clearing completed tasks: ' + error.message);
        }
    });

    // Listeners to close the modal
    closeModalBtn.addEventListener('click', () => taskDetailModal.classList.add('hidden'));
    taskDetailModal.addEventListener('click', (event) => {
        // Close modal if the outer background is clicked
        if (event.target === taskDetailModal) taskDetailModal.classList.add('hidden');
    });

    // Listeners for action buttons inside the modal
    modalTerminateBtn.addEventListener('click', () => { if (currentTaskId) abortTask(currentTaskId); });
    modalRemoveBtn.addEventListener('click', () => { if (currentTaskId) removeTask(currentTaskId); });

    // --- Auto-Refresh Logic ---
    function startAutoRefresh() {
        if (!refreshInterval) {
            refreshInterval = setInterval(loadTasks, 5000); // Refresh every 5 seconds
        }
    }
    function stopAutoRefresh() {
        if (refreshInterval) {
            clearInterval(refreshInterval);
            refreshInterval = null;
        }
    }
    // Pause auto-refresh when the tab is not visible to save resources
    document.addEventListener('visibilitychange', () => {
        document.hidden ? stopAutoRefresh() : startAutoRefresh();
    });

    // --- Initial Load ---
    loadTasks();
    startAutoRefresh();
});
