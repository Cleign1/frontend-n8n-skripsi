document.addEventListener("DOMContentLoaded", function () {
    const footerStatusValue = document.getElementById("footer-status-value");
    const statusIndicator = document.getElementById("status-indicator");
    const lastUpdated = document.getElementById("last-updated");

    if (!footerStatusValue) {
        console.warn("Footer status elements not found.");
        return;
    }

    function getStatusColors(status) {
        const statusLower = (status || "").toLowerCase(); // Add safety check for undefined status
        
        if (statusLower.includes('idle') || statusLower.includes('ready') || statusLower == "") { // Handle empty initial state
            return { indicator: 'bg-gray-400', text: 'text-gray-700' };
        } else if (statusLower.includes('error') || statusLower.includes('❌') || statusLower.includes('gagal')) {
            return { indicator: 'bg-red-500', text: 'text-red-700' };
        } else if (statusLower.includes('completed') || statusLower.includes('selesai') || statusLower.includes('✅') || statusLower.includes('berhasil')) {
            return { indicator: 'bg-green-500', text: 'text-green-700' };
        } else if (statusLower.includes('processing') || statusLower.includes('sending') || statusLower.includes('🔄') || statusLower.includes('📤') || statusLower.includes('memproses') || statusLower.includes('mengirim')) {
            return { indicator: 'bg-blue-500', text: 'text-blue-700' };
        } else if (statusLower.includes('starting') || statusLower.includes('🚀') || statusLower.includes('memulai')) {
            return { indicator: 'bg-yellow-500', text: 'text-yellow-700' };
        } else if (statusLower.includes('terminated') || statusLower.includes('⏹️') || statusLower.includes('dihentikan')) {
            return { indicator: 'bg-orange-500', text: 'text-orange-700' };
        } else {
            return { indicator: 'bg-gray-400', text: 'text-gray-700' };
        }
    }

    function updateStatusDisplay(status, timestamp) {
        const colors = getStatusColors(status);
        
        footerStatusValue.textContent = status || "Loading..."; // Show Loading... if status is empty initially
        footerStatusValue.className = `text-sm font-medium ${colors.text}`;
        
        if (statusIndicator) {
            statusIndicator.className = `w-3 h-3 rounded-full ${colors.indicator}`;
            if (colors.indicator.includes('blue') || colors.indicator.includes('yellow')) {
                statusIndicator.classList.add('animate-pulse');
            } else {
                statusIndicator.classList.remove('animate-pulse');
            }
        }
        
        if (lastUpdated && timestamp) {
            try {
                // Ensure timestamp is valid before creating Date object
                 const date = new Date(timestamp);
                 if (!isNaN(date)) { // Check if date is valid
                     lastUpdated.textContent = date.toLocaleTimeString('id-ID');
                 } else {
                      lastUpdated.textContent = "--:--:--";
                 }
            } catch (e) {
                console.error("Error parsing timestamp:", timestamp, e);
                lastUpdated.textContent = "--:--:--";
            }
        } else {
            lastUpdated.textContent = "--:--:--";
        }
    }

    // --- FETCH INITIAL STATUS ON LOAD ---
    async function fetchInitialFooterStatus() {
        try {
            const response = await fetch("/api/status"); // Still fetch once on load
            if (!response.ok) {
                throw new Error("API server initial fetch failed.");
            }
            const data = await response.json();
            updateStatusDisplay(data.status, data.last_updated);
        } catch (error) {
            console.error("Error fetching initial status for footer:", error);
            updateStatusDisplay("Connection Error", null);
        }
    }

    // --- SOCKET.IO LISTENER FOR REAL-TIME UPDATES ---
    // Force WebSocket-only to avoid invalid session errors across workers
    const socket = io({
        transports: ['websocket'],
        upgrade: false,
        pingInterval: 25000,
        pingTimeout: 20000,
    });

    socket.on('connect', () => {
        console.log('Footer connected via WebSocket.');
        // Fetch initial status once connected
        fetchInitialFooterStatus(); 
    });

    socket.on('disconnect', () => {
        console.error('Footer disconnected from WebSocket.');
        updateStatusDisplay("Disconnected", null); // Show disconnected status
    });

    socket.on('global_status_update', (data) => {
        console.log('Received global status update:', data);
        updateStatusDisplay(data.status, data.last_updated);
    });

    // --- REMOVE POLLING ---
    // The setInterval is no longer needed.
    // setInterval(fetchAndUpdateFooterStatus, 3000); 
});