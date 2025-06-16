// static/javascript/upload_stok.js

document.addEventListener('DOMContentLoaded', function() {
    
    // --- ELEMEN UI ---
    const progressPopup = document.getElementById('progress-popup');
    const progressBar = document.getElementById('progress-bar');
    const progressMessage = document.getElementById('progress-message');
    const closeProgressPopup = document.getElementById('close-progress-popup');
    const sendBtn = document.getElementById('send-full-csv-btn');
    
    // Variabel untuk menampung interval polling
    let pollingIntervalId = null;

    /**
     * Fungsi untuk "bertanya" ke server mengenai status job
     */
    async function checkJobStatus() {
        try {
            const response = await fetch('/api/batch_status');
            const data = await response.json();

            // Tampilkan pop-up jika ada proses atau baru saja selesai
            if (progressPopup) {
                progressPopup.classList.remove('hidden');
                progressBar.style.width = data.progress + '%';
                progressMessage.textContent = data.message;
            }
            
            // Jika proses sudah tidak berjalan (selesai atau error)
            if (!data.is_running) {
                if (pollingIntervalId) {
                    clearInterval(pollingIntervalId);
                    pollingIntervalId = null;
                    console.log("Polling dihentikan karena proses selesai.");
                }
                // Biarkan pop-up terlihat beberapa detik agar pengguna bisa membaca pesan terakhir
                setTimeout(() => {
                    if (progressPopup) progressPopup.classList.add('hidden');
                }, 5000);
            }
        } catch (error) {
            console.error("Gagal melakukan polling status:", error);
            if(progressMessage) progressMessage.textContent = "Gagal cek status.";
            if (pollingIntervalId) clearInterval(pollingIntervalId);
        }
    }

    // --- LOGIKA TOMBOL "MULAI UPDATE" ---
    if (sendBtn) {
        sendBtn.addEventListener('click', async function () {
            const selectedFile = document.getElementById('selected_file').value;
            if (!selectedFile) {
                alert("Pilih atau upload dulu file CSV!");
                return;
            }

            if (pollingIntervalId) clearInterval(pollingIntervalId); // Hentikan polling lama jika ada

            try {
                const response = await fetch('/api/start_batch_process', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ filename: selectedFile })
                });

                const result = await response.json();
                if (!response.ok) throw new Error(result.error || 'Gagal memulai proses.');

                alert(result.message);
                // Setelah proses berhasil dimulai, MULAI POLLING
                checkJobStatus(); // Cek status pertama kali
                pollingIntervalId = setInterval(checkJobStatus, 3000); // Cek setiap 3 detik

            } catch (error) {
                alert('Error: ' + error.message);
            }
        });
    }

    // Cek status saat halaman dimuat, kalau-kalau ada proses yang sedang berjalan
    checkJobStatus();

    // --- LOGIKA MODAL UNTUK "PILIH FILE TERSIMPAN" ---
    const openModalBtn = document.getElementById('open-modal-btn');
    const closeModalBtn = document.getElementById('close-modal-btn');
    const modal = document.getElementById('file-modal');
    const fileList = document.getElementById('file-list');

    if (openModalBtn && modal && closeModalBtn && fileList) {
        openModalBtn.addEventListener('click', () => modal.classList.remove('hidden'));
        closeModalBtn.addEventListener('click', () => modal.classList.add('hidden'));
        modal.addEventListener('click', (event) => {
            if (event.target === modal) modal.classList.add('hidden');
        });
        fileList.addEventListener('click', (event) => {
            if (event.target.tagName === 'LI' && event.target.dataset.filename) {
                document.getElementById('selected_file').value = event.target.dataset.filename;
                document.getElementById('upload-form').submit();
            }
        });
    }
    
    // Logika untuk tombol tutup pop up progress
    if (closeProgressPopup) {
        closeProgressPopup.addEventListener('click', () => {
             if (progressPopup) progressPopup.classList.add('hidden');
             if (pollingIntervalId) clearInterval(pollingIntervalId); // Juga hentikan polling
        });
    }
});