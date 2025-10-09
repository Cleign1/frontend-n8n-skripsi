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
            const selectedDate = datePicker.value;
            if (!selectedDate) {
                alert("Pilih tanggal terlebih dahulu!");
                return;
            }

            // Disable button to prevent multiple clicks while processing
            startUpdateBtn.disabled = true;
            startUpdateBtn.textContent = 'Memulai...';

            try {
                // Call our own backend to safely start the workflow
                const response = await fetch('/api/workflow/start', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ date: selectedDate })
                });

                const result = await response.json();

                if (response.ok) {
                    // On success, the backend gives us a task_id. Redirect to the timeline page.
                    window.location.href = `/workflow/${result.task_id}`;
                } else {
                    // If the backend failed to start the task, show the error
                    throw new Error(result.error || `HTTP error! status: ${response.status}`);
                }
            } catch (error) {
                alert('Error: Gagal memulai proses update stok. ' + error.message);
                // Re-enable the button on failure
                startUpdateBtn.disabled = false;
                startUpdateBtn.textContent = 'Mulai Update Stok';
            }
        });
    }
});
