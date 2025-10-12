document.addEventListener('DOMContentLoaded', function() {
    // --- UI Element Selection ---
    const tasksContainer = document.getElementById('tasks-container');
    const emptyState = document.getElementById('empty-state');
    const refreshBtn = document.getElementById('refresh-btn');
    const clearCompletedBtn = document.getElementById('clear-completed-btn');
    const taskDetailModal = document.getElementById('task-detail-modal');
    const modalTaskName = document.getElementById('modal-task-name');
    const modalTaskContent = document.getElementById('modal-task-content');
    const closeModalBtn = document.getElementById('close-modal-btn');
    const modalTerminateBtn = document.getElementById('modal-terminate-btn');
    const modalRemoveBtn = document.getElementById('modal-remove-btn');
    
    // --- State Variables ---
    let currentTaskId = null;
    let refreshInterval = null;

    // --- Configuration ---
    const statusColors = {
        'PENDING': 'bg-yellow-100 text-yellow-800 border-yellow-200',
        'STARTED': 'bg-blue-100 text-blue-800 border-blue-200',
        'SUCCESS': 'bg-green-100 text-green-800 border-green-200',
        'FAILURE': 'bg-red-100 text-red-800 border-red-200',
        'RETRY': 'bg-orange-100 text-orange-800 border-orange-200',
        'REVOKED': 'bg-gray-100 text-gray-800 border-gray-200',
        'Sedang Prediksi': 'bg-purple-100 text-purple-800 border-purple-200',
        'Prediksi Selesai': 'bg-green-100 text-green-800 border-green-200',
        'Dimulai': 'bg-blue-100 text-blue-800 border-blue-200'
    };

    // --- Helper Functions ---
    function getStatusColor(status) {
        return statusColors[status] || 'bg-gray-100 text-gray-800 border-gray-200';
    }

    function formatDateTime(isoString) {
        if (!isoString) return 'N/A';
        const date = new Date(isoString);
        return date.toLocaleString('id-ID', { year: 'numeric', month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    }

    /**
     * Generates the HTML for a single task card.
     */
    function createTaskCard(task) {
        const statusColor = getStatusColor(task.status);
        
        const isRunning = ['PENDING', 'STARTED', 'Sedang Prediksi', 'RETRY', 'Dimulai'].includes(task.status);
        const isPredictionTask = task.task_id && task.task_id.startsWith('prediksi_');
        const isWorkflowTask = task.task_id && task.task_id.startsWith('workflow_');

        let actionButtonsHtml = '';
        
        // --- FIX IS HERE ---
        if (isWorkflowTask) {
            // It's a workflow task, so ALWAYS show the "Lihat Proses" button.
            // Default to 'update' type for backward compatibility with older tasks.
            const workflowType = task.workflow_type || 'update'; 
            actionButtonsHtml = `
                <a href="/workflow/${workflowType}/${task.task_id}" class="bg-cyan-600 hover:bg-cyan-700 text-white px-3 py-2 rounded-lg text-sm font-medium transition-colors shadow-sm">
                    Lihat Proses
                </a>
            `;
        } else {
            // For all other tasks, show the "Detail" button that opens the modal.
            actionButtonsHtml = `
                <button onclick="showTaskDetail('${task.task_id}')" class="bg-blue-600 hover:bg-blue-700 text-white px-3 py-2 rounded-lg text-sm font-medium transition-colors shadow-sm">
                    Detail
                </button>
            `;
        }

        // Add a second button for terminating or removing the task
        if (isPredictionTask || isWorkflowTask) {
            actionButtonsHtml += `
                <button onclick="removeTask('${task.task_id}')" class="bg-gray-600 hover:bg-gray-700 text-white px-3 py-2 rounded-lg text-sm font-medium transition-colors shadow-sm">
                    Remove
                </button>
            `;
        } else { // It's a standard Celery task
            if (isRunning) {
                actionButtonsHtml += `
                    <button onclick="abortTask('${task.task_id}')" class="bg-red-600 hover:bg-red-700 text-white px-3 py-2 rounded-lg text-sm font-medium transition-colors shadow-sm">
                        Terminate
                    </button>
                `;
            } else {
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

    async function loadTasks() {
        try {
            const response = await fetch('/api/tasks');
            const tasks = await response.json();
            if (tasks.length === 0) {
                tasksContainer.innerHTML = '';
                emptyState.classList.remove('hidden');
            } else {
                emptyState.classList.add('hidden');
                tasks.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
                tasksContainer.innerHTML = tasks.map(createTaskCard).join('');
            }
        } catch (error) {
            console.error('Error loading tasks:', error);
            tasksContainer.innerHTML = `<div class="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700"><p>Error loading tasks: ${error.message}</p></div>`;
        }
    }

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

    window.abortTask = async function(taskId) {
        if (!confirm(`Are you sure you want to abort task ${taskId}?`)) return;
        try {
            const response = await fetch(`/api/tasks/${taskId}/abort`, { method: 'POST' });
            const result = await response.json();
            alert(result.message || result.error);
            loadTasks();
        } catch (error) {
            alert('Error aborting task: ' + error.message);
        }
    };

    window.removeTask = async function(taskId) {
        if (!confirm(`Are you sure you want to remove task ${taskId} from the list?`)) return;
        try {
            const response = await fetch(`/api/tasks/${taskId}/remove`, { method: 'DELETE' });
            if (response.ok) {
                loadTasks();
                if (currentTaskId === taskId) {
                    taskDetailModal.classList.add('hidden');
                }
            } else {
                const result = await response.json();
                alert('Error: ' + result.error);
            }
        } catch (error) {
            alert('Error removing task: ' + error.message);
        }
    };

    refreshBtn.addEventListener('click', loadTasks);
    clearCompletedBtn.addEventListener('click', async function() {
        if (!confirm('Are you sure you want to clear all completed, failed, and revoked tasks?')) return;
        try {
            const response = await fetch('/api/tasks');
            const tasks = await response.json();
            const completedTasks = tasks.filter(task => ['SUCCESS', 'FAILURE', 'REVOKED', 'Prediksi Selesai'].includes(task.status));
            await Promise.all(completedTasks.map(task =>
                fetch(`/api/tasks/${task.task_id}/remove`, { method: 'DELETE' })
            ));
            loadTasks();
        } catch (error) {
            alert('Error clearing completed tasks: ' + error.message);
        }
    });

    closeModalBtn.addEventListener('click', () => taskDetailModal.classList.add('hidden'));
    taskDetailModal.addEventListener('click', (event) => {
        if (event.target === taskDetailModal) taskDetailModal.classList.add('hidden');
    });
    modalTerminateBtn.addEventListener('click', () => { if (currentTaskId) abortTask(currentTaskId); });
    modalRemoveBtn.addEventListener('click', () => { if (currentTaskId) removeTask(currentTaskId); });

    function startAutoRefresh() {
        if (!refreshInterval) {
            refreshInterval = setInterval(loadTasks, 5000);
        }
    }
    function stopAutoRefresh() {
        if (refreshInterval) {
            clearInterval(refreshInterval);
            refreshInterval = null;
        }
    }
    document.addEventListener('visibilitychange', () => {
        document.hidden ? stopAutoRefresh() : startAutoRefresh();
    });

    loadTasks();
    startAutoRefresh();
});