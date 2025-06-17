document.addEventListener('DOMContentLoaded', function() {
    const tasksContainer = document.getElementById('tasks-container');
    const emptyState = document.getElementById('empty-state');
    const refreshBtn = document.getElementById('refresh-btn');
    const clearCompletedBtn = document.getElementById('clear-completed-btn');
    
    // Modal elements
    const taskDetailModal = document.getElementById('task-detail-modal');
    const modalTaskName = document.getElementById('modal-task-name');
    const modalTaskContent = document.getElementById('modal-task-content');
    const closeModalBtn = document.getElementById('close-modal-btn');
    const modalTerminateBtn = document.getElementById('modal-terminate-btn');
    const modalRemoveBtn = document.getElementById('modal-remove-btn');
    
    let currentTaskId = null;
    let refreshInterval = null;

    // Status badge colors with proper Tailwind classes
    const statusColors = {
        'PENDING': 'bg-yellow-100 text-yellow-800 border-yellow-200',
        'STARTED': 'bg-blue-100 text-blue-800 border-blue-200',
        'SUCCESS': 'bg-green-100 text-green-800 border-green-200',
        'FAILURE': 'bg-red-100 text-red-800 border-red-200',
        'RETRY': 'bg-orange-100 text-orange-800 border-orange-200',
        'REVOKED': 'bg-gray-100 text-gray-800 border-gray-200'
    };

    function getStatusColor(status) {
        return statusColors[status] || 'bg-gray-100 text-gray-800 border-gray-200';
    }

    function formatDateTime(isoString) {
        const date = new Date(isoString);
        return date.toLocaleString('id-ID');
    }

    function createTaskCard(task) {
        const statusColor = getStatusColor(task.status);
        const isRunning = ['PENDING', 'STARTED'].includes(task.status);
        
        return `
            <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-md transition-all duration-200" data-task-id="${task.task_id}">
                <div class="flex items-start justify-between">
                    <div class="flex-1">
                        <div class="flex items-center gap-3 mb-3">
                            <h3 class="text-lg font-semibold text-gray-900">${task.task_name || 'Update Stok'}</h3>
                            <span class="px-3 py-1 text-xs font-medium rounded-full border ${statusColor}">
                                ${task.status}
                            </span>
                        </div>
                        
                        <div class="space-y-2 text-sm text-gray-600 mb-4">
                            <p><span class="font-medium text-gray-700">Task ID:</span> <code class="bg-gray-100 px-2 py-1 rounded text-xs">${task.task_id}</code></p>
                            <p><span class="font-medium text-gray-700">File:</span> ${task.filename || 'N/A'}</p>
                            <p><span class="font-medium text-gray-700">Created:</span> ${formatDateTime(task.created_at)}</p>
                            ${task.last_message ? `<p><span class="font-medium text-gray-700">Last Message:</span> <span class="text-gray-900">${task.last_message}</span></p>` : ''}
                        </div>
                        
                        ${isRunning ? `
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
                    
                    <div class="flex gap-2 ml-4">
                        <button onclick="showTaskDetail('${task.task_id}')" class="bg-blue-600 hover:bg-blue-700 text-white px-3 py-2 rounded-lg text-sm font-medium transition-colors shadow-sm">
                            Detail
                        </button>
                        
                        ${isRunning ? `
                            <button onclick="abortTask('${task.task_id}')" class="bg-red-600 hover:bg-red-700 text-white px-3 py-2 rounded-lg text-sm font-medium transition-colors shadow-sm">
                                Terminate
                            </button>
                        ` : `
                            <button onclick="removeTask('${task.task_id}')" class="bg-gray-600 hover:bg-gray-700 text-white px-3 py-2 rounded-lg text-sm font-medium transition-colors shadow-sm">
                                Remove
                            </button>
                        `}
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
                tasksContainer.innerHTML = tasks.map(createTaskCard).join('');
            }
        } catch (error) {
            console.error('Error loading tasks:', error);
            tasksContainer.innerHTML = `
                <div class="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700">
                    <div class="flex items-center">
                        <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path>
                        </svg>
                        Error loading tasks: ${error.message}
                    </div>
                </div>
            `;
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
                    <div class="grid grid-cols-2 gap-4">
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">Task ID</label>
                            <p class="text-sm text-gray-900 font-mono bg-gray-50 p-2 rounded border">${task.task_id}</p>
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">Status</label>
                            <span class="inline-block px-3 py-1 text-xs font-medium rounded-full border ${getStatusColor(task.status)}">
                                ${task.status}
                            </span>
                        </div>
                    </div>
                    
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">Filename</label>
                        <p class="text-sm text-gray-900">${task.filename || 'N/A'}</p>
                    </div>
                    
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">Created At</label>
                        <p class="text-sm text-gray-900">${formatDateTime(task.created_at)}</p>
                    </div>
                    
                    ${task.last_message ? `
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">Last Message</label>
                            <p class="text-sm text-gray-900 bg-gray-50 p-3 rounded border">${task.last_message}</p>
                        </div>
                    ` : ''}
                    
                    ${task.result ? `
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">Result</label>
                            <pre class="text-sm text-gray-900 bg-gray-50 p-3 rounded border overflow-auto max-h-32">${task.result}</pre>
                        </div>
                    ` : ''}
                </div>
            `;
            
            // Show/hide buttons based on task status
            const isRunning = ['PENDING', 'STARTED'].includes(task.status);
            modalTerminateBtn.style.display = isRunning ? 'block' : 'none';
            modalRemoveBtn.style.display = isRunning ? 'none' : 'block';
            
            taskDetailModal.classList.remove('hidden');
            
        } catch (error) {
            console.error('Error loading task detail:', error);
            alert('Error loading task detail: ' + error.message);
        }
    };

        window.abortTask = async function(taskId) {
        if (!confirm(`Are you sure you want to abort task ${taskId}?`)) {
            return;
        }

        // Give immediate visual feedback
        const taskCard = document.querySelector(`[data-task-id="${taskId}"]`);
        if (taskCard) {
            taskCard.style.opacity = '0.5';
        }

        try {
            // FIX: Change the URL to point to our new /abort endpoint
            const response = await fetch(`/api/tasks/${taskId}/abort`, {
                method: 'POST'
            });

            const result = await response.json();

            if (response.ok) {
                alert(result.message);
                loadTasks(); // Refresh the task list
            } else {
                alert('Error: ' + result.error);
                if (taskCard) taskCard.style.opacity = '1'; // Restore on error
            }
        } catch (error) {
            console.error('Error aborting task:', error);
            alert('Error aborting task: ' + error.message);
            if (taskCard) taskCard.style.opacity = '1'; // Restore on error
        }
    };

    window.removeTask = async function(taskId) {
        if (!confirm(`Are you sure you want to remove task ${taskId} from the list?`)) {
            return;
        }
        
        try {
            const response = await fetch(`/api/tasks/${taskId}/remove`, {
                method: 'DELETE'
            });
            
            const result = await response.json();
            
            if (response.ok) {
                loadTasks();
                
                // Close modal if it's open for this task
                if (currentTaskId === taskId) {
                    taskDetailModal.classList.add('hidden');
                }
            } else {
                alert('Error: ' + result.error);
            }
        } catch (error) {
            console.error('Error removing task:', error);
            alert('Error removing task: ' + error.message);
        }
    };

    // Event listeners
    refreshBtn.addEventListener('click', loadTasks);
    
    clearCompletedBtn.addEventListener('click', async function() {
        if (!confirm('Are you sure you want to clear all completed tasks?')) {
            return;
        }
        
        try {
            const response = await fetch('/api/tasks');
            const tasks = await response.json();
            
            const completedTasks = tasks.filter(task => 
                ['SUCCESS', 'FAILURE', 'REVOKED'].includes(task.status)
            );
            
            for (const task of completedTasks) {
                await fetch(`/api/tasks/${task.task_id}/remove`, { method: 'DELETE' });
            }
            
            loadTasks();
        } catch (error) {
            console.error('Error clearing completed tasks:', error);
            alert('Error clearing completed tasks: ' + error.message);
        }
    });

    // Modal event listeners
    closeModalBtn.addEventListener('click', function() {
        taskDetailModal.classList.add('hidden');
    });

    modalTerminateBtn.addEventListener('click', function() {
        if (currentTaskId) {
            terminateTask(currentTaskId);
        }
    });

    modalRemoveBtn.addEventListener('click', function() {
        if (currentTaskId) {
            removeTask(currentTaskId);
        }
    });

    taskDetailModal.addEventListener('click', function(event) {
        if (event.target === taskDetailModal) {
            taskDetailModal.classList.add('hidden');
        }
    });

    // Auto-refresh every 5 seconds
    function startAutoRefresh() {
        refreshInterval = setInterval(loadTasks, 5000);
    }

    function stopAutoRefresh() {
        if (refreshInterval) {
            clearInterval(refreshInterval);
            refreshInterval = null;
        }
    }

    // Start auto-refresh when page loads
    startAutoRefresh();

    // Stop auto-refresh when page is hidden
    document.addEventListener('visibilitychange', function() {
        if (document.hidden) {
            stopAutoRefresh();
        } else {
            startAutoRefresh();
        }
    });

    // Initial load
    loadTasks();
});