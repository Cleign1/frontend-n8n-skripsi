// File: static/javascript/prediksi_stok.js

document.addEventListener('DOMContentLoaded', function() {
    const predictionForm = document.getElementById('prediction-form');

    if (predictionForm) {
        predictionForm.addEventListener('submit', function(event) {
            event.preventDefault();

            const dateInput = document.getElementById('prediction-date');
            const selectedDate = dateInput.value; // Date format is YYYY-MM-DD
            const submitButton = predictionForm.querySelector('button[type="submit"]'); // Get the button

            if (selectedDate) {
                // --- START CHANGE ---
                const dataToSend = {
                    "date": selectedDate, // Use YYYY-MM-DD format as API expects
                    "workflow_type": "prediction"
                };

                // Disable button and show loading state
                submitButton.disabled = true;
                submitButton.textContent = 'Memulai...';

                // Call the workflow start API endpoint directly
                fetch('/api/workflow/start', { // Target the correct endpoint
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(dataToSend)
                })
                .then(response => {
                    // Check if the response status is OK (2xx)
                    if (!response.ok) {
                        // If not OK, try to parse error JSON, otherwise throw HTTP error
                        return response.json().then(errData => {
                            throw new Error(errData.error || `Server responded with status: ${response.status}`);
                        }).catch(() => {
                            // Fallback if response is not JSON or error parsing fails
                            throw new Error(`Server responded with status: ${response.status}`);
                        });
                    }
                    return response.json(); // Parse successful JSON response
                })
                .then(data => {
                    console.log("Workflow started:", data);
                    alert(`Proses prediksi dimulai! Task ID: ${data.task_id}. Anda akan diarahkan ke halaman timeline.`);
                    // Redirect to the workflow timeline page
                    window.location.href = `/workflow/prediction/${data.task_id}`;
                })
                .catch(error => {
                    console.error('Error starting prediction workflow:', error);
                    alert('Gagal memulai proses prediksi: ' + error.message);
                    // Re-enable button on error
                    submitButton.disabled = false;
                    submitButton.textContent = 'Mulai';
                });
                // --- END CHANGE ---

            } else {
                alert('Silakan pilih tanggal terlebih dahulu.');
            }
        });
    }
});