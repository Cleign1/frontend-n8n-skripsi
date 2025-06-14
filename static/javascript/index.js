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
        "font-semibold py-2 px-6 rounded-md shadow-sm transition-all duration-300 bg-red-500 text-white";
    }
  }

  function updateDashboardUI(data) {
    statusIndicator.textContent = data.status || "Unknown";
    
    statusIndicator.className =
      "font-semibold py-2 px-6 rounded-md shadow-sm transition-all duration-300"; // Reset class dasar

    switch ((data.status || "idle").toLowerCase()) {
      case "process":
      case "processing":
      case "running":
        statusIndicator.classList.add("bg-yellow-400", "text-yellow-800");
        break;
      case "completed":
      case "success":
      case "done":
        statusIndicator.classList.add("bg-green-400", "text-green-800");
        break;
      case "failed":
      case "error":
        statusIndicator.classList.add("bg-red-500", "text-white");
        break;
      case "idle":
      default:
        statusIndicator.classList.add("bg-gray-300", "text-gray-800");
        break;
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
  setInterval(fetchAndUpdateStatus, 3000); // Cek status setiap 3 detik
});
