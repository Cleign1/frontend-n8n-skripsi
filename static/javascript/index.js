document.addEventListener("DOMContentLoaded", function () {
  const statusIndicator = document.getElementById("status-indicator");
  const lastUpdateTime = document.getElementById("last-update-time");

  async function fetchAndUpdateStatus() {
    try {
      const response = await fetch("/api/status");
      if (!response.ok) {
        throw new Error("Gagal terhubung ke API server.");
      }
      const data = await response.json();
      updateDashboardUI(data);
    } catch (error) {
      console.error("Error fetching status:", error);
      statusIndicator.textContent = "Error";
      statusIndicator.className =
        "font-semibold py-2 px-6 rounded-md shadow-sm bg-red-500 text-white";
    }
  }

  function updateDashboardUI(data) {
    const status = data.status || "idle";
    statusIndicator.textContent = status;

    statusIndicator.className = "font-semibold py-2 px-6 rounded-md shadow-sm";

    const statusLower = status.toLowerCase();
    if (statusLower.includes('error') || statusLower.includes('❌') || statusLower.includes('gagal')) {
      statusIndicator.classList.add('bg-red-500', 'text-white');
    } else if (statusLower.includes('completed') || statusLower.includes('selesai')) {
      statusIndicator.classList.add('bg-green-500', 'text-white');
    } else if (statusLower.includes('processing') || statusLower.includes('sending') || statusLower.includes('🔄') || statusLower.includes('📤') || statusLower.includes('memproses') || statusLower.includes('mengirim')) {
      statusIndicator.classList.add('bg-blue-500', 'text-white');
    } else if (statusLower.includes('starting') || statusLower.includes('🚀') || statusLower.includes('memulai')) {
      statusIndicator.classList.add('bg-yellow-500', 'text-white');
    } else if (statusLower.includes('terminated') || statusLower.includes('⏹️') || statusLower.includes('dihentikan')) {
      statusIndicator.classList.add('bg-orange-500', 'text-white');
    } else {
      statusIndicator.classList.add('bg-gray-400', 'text-gray-700');
    }

    if (data.last_updated) {
      const date = new Date(data.last_updated);
      const options = {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false,
      };
      lastUpdateTime.textContent = date
        .toLocaleDateString("id-ID", options)
        .replace(/\./g, ":");
    }
  }

  fetchAndUpdateStatus();
  setInterval(fetchAndUpdateStatus, 3000);
});