// File: static/javascript/prediksi_stok.js (VERSI BARU)

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
                        const jsonDataString = JSON.stringify(dataToSend, null, 2);

                        console.log("String JSON yang akan dikirim:", jsonDataString);
                        alert("Data JSON yang akan dikirim ke n8n:\n\n" + jsonDataString);

                        const n8nWebhookUrl = 'http://192.168.1.16:8084/ac25626a-c6bf-4259-b2db-ebc776b3ff08'; // IMPORTANT: REPLACE WITH YOUR N8N WEBHOOK URL

                        // --- FIX: Modified this section to handle empty responses from the webhook ---
                        fetch(n8nWebhookUrl, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: jsonDataString
                        })
                        .then(response => {
                            // We no longer try to parse a JSON response.
                            // We only check if the request was successful (e.g., status 200 OK).
                            if (!response.ok) {
                                throw new Error(`Network response from n8n was not ok. Status: ${response.status}`);
                            }
                            // If we get here, the request was accepted by n8n.
                            console.log('Sukses terkirim ke n8n!');
                            alert('Data berhasil dikirim ke n8n!');
                        })
                        .catch(error => {
                            console.error('Gagal mengirim ke n8n:', error);
                            alert('Terjadi kesalahan saat mengirim data ke n8n.');
                            fetch(`/api/tasks/${task_id}/update`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ status: 'FAILURE', last_message: 'Gagal mengirim request ke n8n.' })
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