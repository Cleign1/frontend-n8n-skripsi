// static/javascript/upload_stok.js

document.addEventListener('DOMContentLoaded', function() {
    
    // --- ELEMEN UI ---
    const uploadGdriveBtn = document.getElementById('upload-gdrive-btn');
    const startUpdateBtn = document.getElementById('start-update-btn');
    const fileInput = document.getElementById('file-input');
    const datePicker = document.getElementById('date-picker');

    function getFormattedDate() {
        const selectedDate = datePicker.value;
        if (!selectedDate) {
            alert("Pilih tanggal terlebih dahulu!");
            return null;
        }
        return selectedDate.replace(/-/g, '');
    }

    if (uploadGdriveBtn) {
        uploadGdriveBtn.addEventListener('click', async function () {
            const clientSideFile = fileInput.files[0];
            const formattedDate = getFormattedDate();

            if (!formattedDate) return;

            if (!clientSideFile && !selectedFileFromServer) {
                alert("Pilih atau upload dulu file CSV!");
                return;
            }

            const formData = new FormData();
            
            if (clientSideFile) {
                formData.append('file', clientSideFile);
            } else {
                formData.append('server_filename', selectedFileFromServer);
            }
            
            formData.append('selected_date', formattedDate);

            try {
                const response = await fetch('/upload/upload_to_gdrive', {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();

                if (response.ok) {
                    alert(result.message || 'File berhasil diupload ke Google Drive.');
                } else {
                    throw new Error(result.error || 'Gagal mengupload file.');
                }

            } catch (error) {
                alert('Error: ' + error.message);
            }
        });
    }

    if (startUpdateBtn) {
        startUpdateBtn.addEventListener('click', async function() {
            const formattedDate = getFormattedDate();
            if (!formattedDate) return;

            const webhookUrl = 'https://n8n.ibnukhaidar.live/webhook/workflow-1-webhook';
            const body = [{ date: formattedDate }];

            try {
                const response = await fetch(webhookUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(body)
                });

                if (response.ok) {
                    const statusMessage = `Proses update stok untuk tanggal ${formattedDate} telah berhasil dimulai.`;
                    alert(statusMessage);

                    // Update the app status via API
                    try {
                        await fetch('/api/status', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ status: statusMessage })
                        });
                    } catch (statusError) {
                        console.error('Failed to update app status:', statusError);
                    }

                } else {
                    const errorResult = await response.json();
                    throw new Error(errorResult.message || `HTTP error! status: ${response.status}`);
                }
            } catch (error) {
                alert('Error: Gagal memulai proses update stok. ' + error.message);
            }
        });
    }
});
