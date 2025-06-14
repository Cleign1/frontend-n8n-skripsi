document.addEventListener('DOMContentLoaded', function() {
    // --- LOGIKA TOMBOL "MULAI UPDATE" ---
    const sendBtn = document.getElementById('send-full-csv-btn');
    if (sendBtn) {
        sendBtn.addEventListener('click', async function () {
            const selectedFile = document.getElementById('selected_file').value;
            if (!selectedFile) {
                alert("Pilih atau upload dulu file CSV untuk ditampilkan!");
                return;
            }
            // ... (sisa logika fetch ke /api/send_full_csv) ...
            console.log(`Mengirim file untuk diupdate: ${selectedFile}`);
        });
    }

    // --- LOGIKA MODAL UNTUK "PILIH FILE TERSIMPAN" ---
    const openModalBtn = document.getElementById('open-modal-btn');
    const closeModalBtn = document.getElementById('close-modal-btn');
    const modal = document.getElementById('file-modal');
    const fileList = document.getElementById('file-list');

    if (openModalBtn && modal && closeModalBtn && fileList) {
        openModalBtn.addEventListener('click', () => {
            modal.classList.remove('hidden');
        });

        closeModalBtn.addEventListener('click', () => {
            modal.classList.add('hidden');
        });

        modal.addEventListener('click', (event) => {
            if (event.target === modal) {
                modal.classList.add('hidden');
            }
        });

        fileList.addEventListener('click', (event) => {
            if (event.target.tagName === 'LI' && event.target.dataset.filename) {
                const filename = event.target.dataset.filename;
                const hiddenSelect = document.getElementById('selected_file');
                hiddenSelect.value = filename;
                document.getElementById('upload-form').submit();
            }
        });
    }
});