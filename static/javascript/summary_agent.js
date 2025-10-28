document.addEventListener('DOMContentLoaded', function() {
    const startButton = document.getElementById('start-summary-btn');
    const notificationArea = document.getElementById('notification-area');
    
    // === NEW: Get the date input element ===
    const dateInput = document.getElementById('summary-date-input');

    if (!startButton || !dateInput) {
        // If elements are missing, do nothing
        return;
    }

    // Get the URLs from the data attributes on the button
    const startUrl = startButton.dataset.startUrl;
    const tasksUrl = startButton.dataset.tasksUrl;

    startButton.addEventListener('click', function() {
        notificationArea.innerHTML = ''; // Clear previous notifications

        // === MODIFIED: Read value from the date input ===
        const selectedDate = dateInput.value;

        // === NEW: Validate that a date was selected ===
        if (!selectedDate) {
            notificationArea.innerHTML = `<p class="text-red-700">❌ Harap pilih tanggal terlebih dahulu.</p>`;
            return; // Stop the function
        }

        // Disable the button to prevent multiple clicks
        startButton.disabled = true;
        startButton.textContent = 'Memulai...';
        startButton.classList.add('bg-gray-400');

        // Create the payload object with the *selected* date
        const payload = {
            date: selectedDate
        };

        // Make the API call to the Flask endpoint
        fetch(startUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            // Send the payload with the selected date
            body: JSON.stringify(payload)
        })
        .then(response => {
            if (!response.ok) {
                // Handle HTTP errors
                throw new Error(`Server responded with status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // Handle success
            notificationArea.innerHTML = `
                <p class="text-green-700">✅ Tugas berhasil dimulai (ID: ${data.task_id}).</p>
                <p class="text-gray-600 mt-1">Anda sekarang dapat memantau progresnya di <a href="${tasksUrl}" class="font-bold text-blue-600 hover:underline">Halaman Tugas</a>.</p>
            `;
        })
        .catch(error => {
            // Handle failure
            console.error('Error:', error);
            notificationArea.innerHTML = `<p class="text-red-700">❌ Gagal memulai tugas. Silakan periksa konsol atau log server.</p>`;
        })
        .finally(() => {
            // Re-enable the button
            startButton.disabled = false;
            startButton.textContent = 'Mulai Proses Analisis';
            startButton.classList.remove('bg-gray-400');
        });
    });
});