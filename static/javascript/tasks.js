// static/javascript/tasks.js
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
        'Prediksi Selesai': 'bg-green-100 text-green-800 border-green-200', // Added for consistency
        'Dimulai': 'bg-blue-100 text-blue-800 border-blue-200',
        'ABORTED': 'bg-gray-400 text-gray-900 border-gray-500' // Added for aborted tasks
    };

    // --- Helper Functions ---
    function getStatusColor(status) {
        return statusColors[status] || 'bg-gray-100 text-gray-800 border-gray-200';
    }

    function formatDateTime(isoString) {
        if (!isoString) return 'N/A';
        try {
            const date = new Date(isoString);
             // Check if date is valid before formatting
            if (isNaN(date.getTime())) {
                return 'Invalid Date';
            }
            return date.toLocaleString('id-ID', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
        } catch (e) {
            console.error("Error formatting date:", isoString, e);
            return 'Invalid Date';
        }
    }


    /**
     * Generates the HTML for a single task card.
     */
    function createTaskCard(task) {
        const statusColor = getStatusColor(task.status);

        const isRunning = ['PENDING', 'STARTED', 'Sedang Prediksi', 'RETRY', 'Dimulai'].includes(task.status);
        // Ensure task_id is treated as a string for startsWith check
        const taskIdStr = String(task.task_id || '');
        const isPredictionTask = taskIdStr.startsWith('prediksi_');
        const isWorkflowTask = taskIdStr.startsWith('workflow_');
        const workflowType = task.workflow_type || 'update'; // Default for safety

        let actionButtonsHtml = '';

        if (isWorkflowTask) {
            // --- START FIX: Use 'report' for URL if workflow_type is 'summary' ---
            const linkWorkflowType = (workflowType === 'summary') ? 'report' : workflowType;
            actionButtonsHtml = `
                <a href="/workflow/${linkWorkflowType}/${task.task_id}" class="bg-cyan-600 hover:bg-cyan-700 text-white px-3 py-2 rounded-lg text-sm font-medium transition-colors shadow-sm">
                    Lihat Proses
                </a>
            `;
             // --- END FIX ---

        } else if (isPredictionTask) {
             // For prediction tasks (prediksi_), show Detail (which opens modal) instead of Lihat Proses
             actionButtonsHtml = `
                <button onclick="showTaskDetail('${task.task_id}')" class="bg-blue-600 hover:bg-blue-700 text-white px-3 py-2 rounded-lg text-sm font-medium transition-colors shadow-sm">
                    Detail
                </button>
            `;
        } else {
            // For standard Celery tasks, show Detail (which opens modal).
            actionButtonsHtml = `
                <button onclick="showTaskDetail('${task.task_id}')" class="bg-blue-600 hover:bg-blue-700 text-white px-3 py-2 rounded-lg text-sm font-medium transition-colors shadow-sm">
                    Detail
                </button>
            `;
        }


        // Add Remove/Terminate button based on task type and status
        if (isPredictionTask || isWorkflowTask) {
            // Workflow and Prediction tasks can always be removed
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
                <div class="flex items-start justify-between flex-wrap gap-y-4">
                    <div class="flex-1 min-w-[200px] pr-4">
                        <div class="flex items-center gap-3 mb-3 flex-wrap">
                            <h3 class="text-lg font-semibold text-gray-900">${task.task_name || 'Unnamed Task'}</h3>
                            <span class="px-3 py-1 text-xs font-medium rounded-full border ${statusColor}">
                                ${task.status || 'UNKNOWN'}
                            </span>
                        </div>
                        <div class="space-y-2 text-sm text-gray-600 mb-4 break-words">
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
                    <div class="flex flex-col sm:flex-row gap-2 ml-0 sm:ml-4 flex-shrink-0">
                        ${actionButtonsHtml}
                    </div>
                </div>
            </div>
        `;
    }

    async function loadTasks() {
        try {
            const response = await fetch('/api/tasks');
            if (!response.ok) {
                 throw new Error(`HTTP error! status: ${response.status}`);
            }
            const tasks = await response.json();
            if (!Array.isArray(tasks)) {
                 throw new Error("Invalid response format: Expected an array of tasks.");
            }

            if (tasks.length === 0) {
                tasksContainer.innerHTML = ''; // Clear previous tasks
                emptyState.classList.remove('hidden');
            } else {
                emptyState.classList.add('hidden');
                // Ensure sorting works even if created_at is missing or invalid
                tasks.sort((a, b) => {
                     const dateA = a.created_at ? new Date(a.created_at).getTime() : 0;
                     const dateB = b.created_at ? new Date(b.created_at).getTime() : 0;
                     // Handle invalid dates by pushing them to the end
                     if (isNaN(dateA) && isNaN(dateB)) return 0;
                     if (isNaN(dateA)) return 1;
                     if (isNaN(dateB)) return -1;
                     return dateB - dateA; // Sort descending (newest first)
                 });
                tasksContainer.innerHTML = tasks.map(createTaskCard).join('');
            }
        } catch (error) {
            console.error('Error loading tasks:', error);
            tasksContainer.innerHTML = `<div class="bg-red-100 border border-red-300 rounded-xl p-4 text-red-800"><p>Error loading tasks: ${error.message}. Please try refreshing.</p></div>`;
            emptyState.classList.add('hidden'); // Hide empty state on error
        }
    }


    window.showTaskDetail = async function(taskId) {
        currentTaskId = taskId;
        try {
            const response = await fetch(`/api/tasks/${taskId}/status`);
             if (!response.ok) {
                 throw new Error(`HTTP error! status: ${response.status}`);
            }
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
            const isRunning = ['PENDING', 'STARTED', 'Sedang Prediksi', 'RETRY', 'Dimulai'].includes(task.status);
             // Ensure task_id is treated as a string for startsWith check
            const taskIdStr = String(task.task_id || '');
            const isPredictionTask = taskIdStr.startsWith('prediksi_');
            const isWorkflowTask = taskIdStr.startsWith('workflow_'); // Check if it's a workflow task

            // Show Terminate only for standard Celery tasks that are running
            modalTerminateBtn.style.display = isRunning && !isPredictionTask && !isWorkflowTask ? 'block' : 'none';
            // Show Remove for finished standard tasks, and ALL workflow/prediction tasks
            modalRemoveBtn.style.display = (!isRunning && !isPredictionTask && !isWorkflowTask) || isPredictionTask || isWorkflowTask ? 'block' : 'none';

            taskDetailModal.classList.remove('hidden');
        } catch (error) {
            console.error('Error loading task detail:', error);
            alert('Error loading task detail: ' + error.message);
        }
    };

    window.abortTask = async function(taskId) {
        if (!confirm(`Are you sure you want to abort task ${taskId}? This might take a moment.`)) return;
        try {
            const response = await fetch(`/api/tasks/${taskId}/abort`, { method: 'POST' });
             const result = await response.json();
             if (!response.ok) {
                 throw new Error(result.error || `HTTP error! status: ${response.status}`);
             }
            alert(result.message || 'Abort signal sent.');
            // Give Redis a moment to update before reloading
            setTimeout(loadTasks, 1000);
        } catch (error) {
             console.error('Error aborting task:', error);
            alert('Error aborting task: ' + error.message);
        }
    };

    window.removeTask = async function(taskId) {
        if (!confirm(`Are you sure you want to remove task ${taskId} from the list?`)) return;
        try {
            const response = await fetch(`/api/tasks/${taskId}/remove`, { method: 'DELETE' });
            if (response.ok) {
                // Find and remove the card directly from the DOM for instant feedback
                 const taskCard = tasksContainer.querySelector(`[data-task-id="${taskId}"]`);
                 if (taskCard) {
                     taskCard.remove();
                 }
                 // Check if container is now empty
                 if (!tasksContainer.hasChildNodes()) {
                     emptyState.classList.remove('hidden');
                 }
                // Close modal if the removed task was being viewed
                if (currentTaskId === taskId) {
                    taskDetailModal.classList.add('hidden');
                     currentTaskId = null; // Reset current task ID
                }
                 // Optional: Reload tasks after a short delay to ensure consistency,
                 // but removing from DOM gives better immediate feedback.
                 // setTimeout(loadTasks, 500);
            } else {
                const result = await response.json();
                throw new Error(result.error || `HTTP error! status: ${response.status}`);
            }
        } catch (error) {
            console.error('Error removing task:', error);
            alert('Error removing task: ' + error.message);
        }
    };


    refreshBtn.addEventListener('click', loadTasks);

    clearCompletedBtn.addEventListener('click', async function() {
        if (!confirm('Are you sure you want to clear all completed, failed, and revoked tasks?')) return;
        try {
             // Fetch only task IDs and statuses needed for filtering
            const response = await fetch('/api/tasks');
             if (!response.ok) {
                 throw new Error(`HTTP error! status: ${response.status}`);
             }
            const tasks = await response.json();
            if (!Array.isArray(tasks)) {
                 throw new Error("Invalid response format: Expected an array of tasks.");
            }

            const completedTaskIds = tasks
                .filter(task => ['SUCCESS', 'FAILURE', 'REVOKED', 'Prediksi Selesai', 'ABORTED'].includes(task.status))
                .map(task => task.task_id);

             if (completedTaskIds.length === 0) {
                 alert("No completed tasks to clear.");
                 return;
             }

             // Send all IDs to be removed in a single request (if backend supports it)
             // OR loop through and remove one by one (current implementation)
             console.log("Clearing tasks:", completedTaskIds);
            const removalPromises = completedTaskIds.map(taskId =>
                fetch(`/api/tasks/${taskId}/remove`, { method: 'DELETE' })
                     .then(res => {
                         if (!res.ok) console.warn(`Failed to remove task ${taskId}`);
                         return res.ok;
                     })
                     .catch(err => {
                         console.error(`Error removing task ${taskId}:`, err);
                         return false;
                     })
            );

            await Promise.all(removalPromises);
             console.log("Clear completed finished.");
            // Reload tasks after clearing
            loadTasks();

        } catch (error) {
             console.error('Error clearing completed tasks:', error);
            alert('Error clearing completed tasks: ' + error.message);
        }
    });

    closeModalBtn.addEventListener('click', () => {
         taskDetailModal.classList.add('hidden');
         currentTaskId = null; // Reset current task ID
     });

    taskDetailModal.addEventListener('click', (event) => {
        // Close modal if backdrop is clicked
        if (event.target === taskDetailModal) {
             taskDetailModal.classList.add('hidden');
             currentTaskId = null; // Reset current task ID
         }
    });
    modalTerminateBtn.addEventListener('click', () => { if (currentTaskId) abortTask(currentTaskId); });
    modalRemoveBtn.addEventListener('click', () => { if (currentTaskId) removeTask(currentTaskId); });

    // --- Auto-Refresh Logic ---
    function startAutoRefresh() {
        if (refreshInterval) {
             clearInterval(refreshInterval); // Clear existing interval if any
         }
        // Refresh every 7 seconds
        refreshInterval = setInterval(loadTasks, 7000);
         console.log("Auto-refresh started.");
    }
    function stopAutoRefresh() {
        if (refreshInterval) {
            clearInterval(refreshInterval);
            refreshInterval = null;
             console.log("Auto-refresh stopped.");
        }
    }

    // Pause refresh when the page is not visible
    document.addEventListener('visibilitychange', () => {
         console.log("Visibility changed:", document.hidden);
        if (document.hidden) {
             stopAutoRefresh();
         } else {
             // Reload immediately when tab becomes visible again, then restart interval
             loadTasks();
             startAutoRefresh();
         }
    });

    // Initial load and start refresh
    loadTasks();
    startAutoRefresh();

     // Optional: Stop refresh if modal is open to prevent background changes
     const observer = new MutationObserver(mutations => {
         mutations.forEach(mutation => {
             if (mutation.attributeName === 'class') {
                 const isHidden = taskDetailModal.classList.contains('hidden');
                 if (isHidden && !document.hidden) {
                     startAutoRefresh(); // Restart if modal closed and page visible
                 } else if (!isHidden) {
                     stopAutoRefresh(); // Stop if modal opened
                 }
             }
         });
     });
     observer.observe(taskDetailModal, { attributes: true });


}); // End DOMContentLoaded