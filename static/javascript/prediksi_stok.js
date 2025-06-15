// File: static/javascript/prediksi_stok.js (VERSI BARU)

document.addEventListener('DOMContentLoaded', function() {
    
    const predictionForm = document.getElementById('prediction-form');

    if (predictionForm) {
        
        predictionForm.addEventListener('submit', function(event) {
            
            event.preventDefault();

            const dateInput = document.getElementById('prediction-date');
            const selectedDate = dateInput.value;

            if (selectedDate) {
                // --- PERUBAHAN UTAMA ADA DI SINI ---

                // 1. Buat sebuah object JavaScript dengan data yang ingin dikirim.
                //    Kunci (key) di sini (misal: "prediction_date") akan menjadi
                //    nama field di n8n nantinya.
                const dataToSend = {
                    prediction_date: selectedDate,
                    request_time: new Date().toISOString() // Contoh menambahkan data lain
                };

                // 2. Konversi object JavaScript menjadi string JSON.
                //    Ini adalah format teks yang akan dikirim melalui jaringan.
                //    Argumen 'null, 2' membuatnya lebih rapi (pretty-print).
                const jsonDataString = JSON.stringify(dataToSend, null, 2);

                // 3. Tampilkan output untuk debugging dan konfirmasi.
                
                // Tampilkan di console browser (tekan F12 untuk melihat).
                // Ini sangat berguna untuk memastikan object dan format JSON sudah benar.
                console.log("Object JavaScript yang dibuat:", dataToSend);
                console.log("String JSON yang akan dikirim:", jsonDataString);

                // Tampilkan di pop-up alert agar langsung terlihat.
                alert("Data JSON yang akan dikirim ke n8n:\n\n" + jsonDataString);

                // --- LANGKAH SELANJUTNYA: MENGIRIM DATA KE N8N ---
                // Kode di bawah ini bisa Anda aktifkan (hapus komentar //) 
                // jika sudah siap mengirim data.
                /*
                const n8nWebhookUrl = 'URL_WEBHOOK_N8N_ANDA_DISINI';

                fetch(n8nWebhookUrl, {
                    method: 'POST', // Metode untuk mengirim data
                    headers: {
                        'Content-Type': 'application/json' // Memberi tahu server kita mengirim JSON
                    },
                    body: jsonDataString // Body request berisi string JSON
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Network response was not ok');
                    }
                    return response.json(); // Mengambil response dari n8n
                })
                .then(data => {
                    console.log('Sukses terkirim ke n8n:', data);
                    alert('Data berhasil dikirim ke n8n!');
                })
                .catch(error => {
                    console.error('Gagal mengirim ke n8n:', error);
                    alert('Terjadi kesalahan saat mengirim data.');
                });
                */

            } else {
                alert('Silakan pilih tanggal terlebih dahulu.');
            }
        });
    }
});