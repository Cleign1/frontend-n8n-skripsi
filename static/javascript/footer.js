document.addEventListener("DOMContentLoaded", function () {
    const footerStatusValue = document.getElementById("footer-status-value");
    const statusIndicator = document.getElementById("status-indicator");
    const lastUpdated = document.getElementById("last-updated");

    if (!footerStatusValue) {
        return;
    }

    /**
     * Get appropriate Tailwind color classes based on status
     */
    function getStatusColors(status) {
        const statusLower = status.toLowerCase();
        
        if (statusLower.includes('idle') || statusLower.includes('ready')) {
            return {
                indicator: 'bg-gray-400',
                text: 'text-gray-700'
            };
        } else if (statusLower.includes('error') || statusLower.includes('❌') || statusLower.includes('gagal')) {
            return {
                indicator: 'bg-red-500',
                text: 'text-red-700'
            };
        } else if (statusLower.includes('completed') || statusLower.includes('selesai') || statusLower.includes('✅') || statusLower.includes('berhasil')) {
            return {
                indicator: 'bg-green-500',
                text: 'text-green-700'
            };
        } else if (statusLower.includes('processing') || statusLower.includes('sending') || statusLower.includes('🔄') || statusLower.includes('📤') || statusLower.includes('memproses') || statusLower.includes('mengirim')) {
            return {
                indicator: 'bg-blue-500',
                text: 'text-blue-700'
            };
        } else if (statusLower.includes('starting') || statusLower.includes('🚀') || statusLower.includes('memulai')) {
            return {
                indicator: 'bg-yellow-500',
                text: 'text-yellow-700'
            };
        } else if (statusLower.includes('terminated') || statusLower.includes('⏹️') || statusLower.includes('dihentikan')) {
            return {
                indicator: 'bg-orange-500',
                text: 'text-orange-700'
            };
        } else {
            return {
                indicator: 'bg-gray-400',
                text: 'text-gray-700'
            };
        }
    }

    /**
     * Update status with proper colors and formatting
     */
    function updateStatusDisplay(status, timestamp) {
        const colors = getStatusColors(status);
        
        // Update status text
        footerStatusValue.textContent = status;
        footerStatusValue.className = `text-sm font-medium ${colors.text}`;
        
        // Update status indicator
        if (statusIndicator) {
            statusIndicator.className = `w-3 h-3 rounded-full ${colors.indicator}`;
            
            // Add pulse animation for active states
            if (colors.indicator.includes('blue') || colors.indicator.includes('yellow')) {
                statusIndicator.classList.add('animate-pulse');
            } else {
                statusIndicator.classList.remove('animate-pulse');
            }
        }
        
        // Update timestamp
        if (lastUpdated && timestamp) {
            const date = new Date(timestamp);
            lastUpdated.textContent = date.toLocaleTimeString('id-ID');
        }
    }

    /**
     * Fetch status from API and update display
     */
    async function fetchAndUpdateFooterStatus() {
        try {
            const response = await fetch("/api/status");
            if (!response.ok) {
                throw new Error("API server tidak merespon.");
            }
            const data = await response.json();
            
            updateStatusDisplay(data.status || "Unknown", data.last_updated);

        } catch (error) {
            console.error("Error fetching status for footer:", error);
            updateStatusDisplay("Connection Error", null);
        }
    }

    // Initial load
    fetchAndUpdateFooterStatus();

    // Auto-refresh every 3 seconds
    setInterval(fetchAndUpdateFooterStatus, 3000);
});