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
                    "prediction_date": selectedDate,
                    "task_id": task_id
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
                        // Task created successfully, now send the request to the prediction service.
                        console.log("Task created, now sending to prediction service.");
                        alert("Task dibuat. Mengirim permintaan prediksi ke server...");

                        // Send the request to our own backend proxy endpoint.
                        fetch('/api/predict_stok', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify(dataToSend)
                        })
                        .then(proxyResponse => {
                            if (!proxyResponse.ok) {
                                return proxyResponse.json().then(err => { throw new Error(err.error || `Proxy server failed with status: ${proxyResponse.status}`); });
                            }
                            console.log('Sukses terkirim ke layanan prediksi via proxy!');
                            alert('Data berhasil dikirim untuk prediksi!');
                        })
                        .catch(error => {
                            console.error('Gagal mengirim ke layanan prediksi via proxy:', error);
                            alert('Terjadi kesalahan saat mengirim data untuk prediksi: ' + error.message);
                            // Update the task to show failure
                            fetch(`/api/tasks/${task_id}/update`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ status: 'FAILURE', last_message: `Gagal mengirim request via proxy: ${error.message}` })
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
