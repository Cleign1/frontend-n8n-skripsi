document.addEventListener("DOMContentLoaded", function () {
    // Targetkan elemen SPAN spesifik tempat nilai status akan ditampilkan.
    // Pastikan ID ini ada di file footer.html Anda.
    const footerStatusValue = document.getElementById("footer-status-value");

    // Jika elemen span untuk status tidak ditemukan di halaman, hentikan skrip.
    // Ini membuat skrip aman dijalankan di halaman mana pun.
    if (!footerStatusValue) {
        return;
    }

    /**
     * Fungsi untuk mengambil status dari API dan HANYA memperbarui teks di footer.
     */
    async function fetchAndUpdateFooterStatus() {
        try {
            const response = await fetch("/api/status");
            if (!response.ok) {
                throw new Error("API server tidak merespon.");
            }
            const data = await response.json();
            // Hanya perbarui teks di dalam span. Tidak ada logika warna atau elemen lain.
            footerStatusValue.textContent = data.status || "Unknown";

        } catch (error) {
            console.error("Error fetching status for footer:", error);
            footerStatusValue.textContent = "Connection Error";
        }
    }

    // Panggil pertama kali untuk mendapatkan status awal.
    fetchAndUpdateFooterStatus();

    // Atur agar status di-refresh setiap 5 detik.
    setInterval(fetchAndUpdateFooterStatus, 5000);
});