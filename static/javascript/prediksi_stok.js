// File: static/javascript/prediksi_stok.js

document.addEventListener('DOMContentLoaded', function() {

    const predictionForm = document.getElementById('prediction-form');

    if (predictionForm) {

        predictionForm.addEventListener('submit', function(event) {

            event.preventDefault();

            const dateInput = document.getElementById('prediction-date');
            const selectedDate = dateInput.value;

            if (selectedDate) {
                const task_name = `Prediksi Stok ${new Date().toISOString()}`;
                const task_id = "prediksi_" + new Date().getTime();

                const dataToSend = {
                    prediction_date: selectedDate,
                    request_time: new Date().toISOString(),
                    task_id: task_id,
                };

                const task = {
                    task_id: task_id,
                    task_name: task_name,
                    filename: 'N/A',
                    created_at: new Date().toISOString(),
                    status: 'Sedang Prediksi',
                    last_message: 'Menunggu prediksi dari n8n...'
                };

                // First, create the task in our own system.
                fetch('/api/tasks/create', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(task)
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`Network response was not ok, status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    if(data.status === 'success') {
                        // Task created successfully, now send the request to our backend proxy.
                        console.log("Task created, now sending to backend proxy.");
                        alert("Task dibuat. Mengirim permintaan prediksi ke server...");

                        // --- MODIFICATION ---
                        // Send the request to our own backend proxy endpoint instead of directly to n8n.
                        fetch('/api/forward_prediction', { // NEW, LOCAL ENDPOINT
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify(dataToSend) // Send the data intended for n8n
                        })
                        .then(proxyResponse => {
                            if (!proxyResponse.ok) {
                                // If the proxy itself returns an error, handle it.
                                return proxyResponse.json().then(err => { throw new Error(err.error || `Proxy server failed with status: ${proxyResponse.status}`); });
                            }
                            console.log('Sukses terkirim ke n8n via proxy!');
                            alert('Data berhasil dikirim ke n8n!');
                        })
                        .catch(error => {
                            // This catch now handles failures from the proxy request.
                            console.error('Gagal mengirim ke n8n via proxy:', error);
                            alert('Terjadi kesalahan saat mengirim data ke n8n: ' + error.message);
                            // Update the task to show failure
                            fetch(`/api/tasks/${task_id}/update`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ status: 'FAILURE', last_message: `Gagal mengirim request ke n8n: ${error.message}` })
                            });
                        });
                    }
                })
                .catch(error => {
                    console.error('Error creating task:', error);
                    alert('Gagal membuat task baru. Lihat console untuk detail.');
                });

            } else {
                alert('Silakan pilih tanggal terlebih dahulu.');
            }
        });
    }
});