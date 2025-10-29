document.addEventListener('DOMContentLoaded', function() {
    const startButton = document.getElementById('start-summary-btn');
    const notificationArea = document.getElementById('notification-area');

    // The button might not exist if the user is on another page
    if (!startButton) {
        return;
    }

    // Get the URLs from the data attributes on the button
    const startUrl = startButton.dataset.startUrl;
    const tasksUrl = startButton.dataset.tasksUrl;

    startButton.addEventListener('click', function() {
        // Disable the button to prevent multiple clicks
        startButton.disabled = true;
        startButton.textContent = 'Starting...';
        startButton.classList.add('bg-gray-400');
        notificationArea.textContent = ''; // Clear previous notifications

        // Make the API call to the Flask endpoint using the URL from the data attribute
        fetch(startUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => {
            if (!response.ok) {
                // Handle HTTP errors
                throw new Error(`Server responded with status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // Handle success by creating a notification with a link to the tasks page
            notificationArea.innerHTML = `
                <p class="text-green-700">✅ Task started successfully (ID: ${data.task_id}).</p>
                <p class="text-gray-600 mt-1">You can now monitor its progress on the <a href="${tasksUrl}" class="font-bold text-blue-600 hover:underline">Tasks Page</a>.</p>
            `;
        })
        .catch(error => {
            // Handle failure (network error or bad response)
            console.error('Error:', error);
            notificationArea.innerHTML = `<p class="text-red-700">❌ Failed to start the task. Please check the console or server logs.</p>`;
        })
        .finally(() => {
            // Re-enable the button after the request is complete
            startButton.disabled = false;
            startButton.textContent = 'Start Summary Process';
            startButton.classList.remove('bg-gray-400');
        });
    });
});