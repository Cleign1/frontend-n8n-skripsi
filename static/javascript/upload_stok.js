// static/javascript/upload_stok.js

document.addEventListener('DOMContentLoaded', function() {

    // --- UI ELEMENTS ---
    const uploadGdriveBtn = document.getElementById('upload-gdrive-btn');
    const workflowStartBtn = document.getElementById('start-update-btn');
    const fileInput = document.getElementById('file-input'); // Although handled by submit, keep for reference
    const gdriveDatePicker = document.getElementById('gdrive-date-picker');
    const workflowDatePicker = document.getElementById('workflow-date-picker');
    const workflowDateMessage = document.getElementById('workflow-date-message');
    const gdriveDateMessage = document.getElementById('gdrive-date-message');

    // --- UTILITY FUNCTIONS ---
    function getFormattedDate(datePicker) {
        const selectedDate = datePicker.value;
        if (!selectedDate) {
            return null;
        }
        // Returns date string in YYYY-MM-DD format as needed by backend
        return selectedDate;
    }

    // --- TOGGLE FUNCTIONS ---

    /**
     * Toggles the state of the main workflow button (Start Update Stok).
     * Enabled only by date selection in the workflow date picker.
     */
    function toggleWorkflowStartButton() {
        if (!workflowStartBtn || !workflowDatePicker) return; // Guard clause

        const selectedDate = workflowDatePicker.value;
        const isDateSelected = !!selectedDate;

        workflowStartBtn.disabled = !isDateSelected; // Directly set disabled state

        if (isDateSelected) {
            workflowDateMessage.classList.add('hidden');
        }
        // Note: Tailwind's `disabled:` modifier handles the visual state
    }

    /**
     * Toggles the state of the Google Drive upload button (Upload to CDN).
     * Enabled only if a file is on the server AND a date is selected in its block.
     */
    function toggleGdriveUploadButton() {
        if (!uploadGdriveBtn || !gdriveDatePicker) return; // Guard clause

        const isFilePresent = !!selectedFileFromServer; // Check if Flask provided a filename
        const isDateSelected = !!gdriveDatePicker.value;

        const shouldEnable = isFilePresent && isDateSelected;

        uploadGdriveBtn.disabled = !shouldEnable; // Directly set disabled state

        // Show message only if file is present but date is missing
        if (isFilePresent && !isDateSelected) {
            gdriveDateMessage.classList.remove('hidden');
        } else {
            gdriveDateMessage.classList.add('hidden');
        }
        // Note: Tailwind's `disabled:` modifier handles the visual state
    }


    // --- INITIAL STATE SETUP ---
    toggleWorkflowStartButton();
    toggleGdriveUploadButton(); // Initial check for GDrive button state

    // --- EVENT LISTENERS ---

    // 1. Listen for workflow date changes
    if (workflowDatePicker) {
        workflowDatePicker.addEventListener('change', toggleWorkflowStartButton);
        workflowDatePicker.addEventListener('input', toggleWorkflowStartButton); // Also on input for immediate feedback
    }

    // 2. Listen for GDrive date changes
    if (gdriveDatePicker) {
        gdriveDatePicker.addEventListener('change', toggleGdriveUploadButton);
        gdriveDatePicker.addEventListener('input', toggleGdriveUploadButton); // Also on input
    }


    // 3. Upload to Google Drive Button Handler (Upload to CDN)
    if (uploadGdriveBtn) {
        uploadGdriveBtn.addEventListener('click', async function () {

            // Check file again (should be guaranteed by toggle logic, but safe)
            if (!selectedFileFromServer) {
                console.error("Upload Error: No file selected on server.");
                alert("Kesalahan: Tidak ada file di server untuk diupload.");
                return;
            }

            const formattedDate = getFormattedDate(gdriveDatePicker);

            if (!formattedDate) {
                 // Should not happen if button is enabled, but good check
                gdriveDateMessage.classList.remove('hidden');
                console.error("Upload Error: Date not selected for CDN upload.");
                alert("Pilih tanggal untuk penamaan file di CDN!");
                return;
            }
            gdriveDateMessage.classList.add('hidden');

            // --- UI Feedback Start ---
            const originalText = uploadGdriveBtn.textContent;
            uploadGdriveBtn.disabled = true;
            uploadGdriveBtn.textContent = 'Uploading...';
            // Tailwind handles visual disabling via `disabled:` styles

            const formData = new FormData();
            formData.append('server_filename', selectedFileFromServer);
            formData.append('selected_date', formattedDate);

            try {
                const response = await fetch('/upload/upload_to_gdrive', {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();

                if (response.ok) {
                    alert(result.message || 'File berhasil diupload ke CDN (Google Drive).');
                } else {
                    throw new Error(result.error || 'Gagal mengupload file ke CDN.');
                }

            } catch (error) {
                console.error("CDN Upload Error:", error);
                alert('Error: ' + error.message);
            } finally {
                // --- UI Feedback End ---
                uploadGdriveBtn.textContent = originalText;
                // Re-evaluate button state based on current conditions
                toggleGdriveUploadButton();
            }
        });
    }

    // 4. Start Update Stock Workflow Button Handler (Triggers n8n from CDN)
    if (workflowStartBtn) {
        workflowStartBtn.addEventListener('click', async function() {
            const selectedDate = getFormattedDate(workflowDatePicker);
            if (!selectedDate) {
                workflowDateMessage.classList.remove('hidden');
                alert("Pilih tanggal update terlebih dahulu!");
                return;
            }
            workflowDateMessage.classList.add('hidden');

            // --- UI Feedback Start ---
            const originalText = workflowStartBtn.textContent;
            workflowStartBtn.disabled = true;
            workflowStartBtn.textContent = 'Memulai...';
             // Tailwind handles visual disabling via `disabled:` styles

            try {
                // Call backend to start the n8n workflow
                const response = await fetch('/api/workflow/start', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ date: selectedDate, workflow_type: 'update' })
                });

                const result = await response.json();

                if (response.ok) {
                    // Redirect to the timeline page on success
                    window.location.href = `/workflow/update/${result.task_id}`;
                } else {
                    throw new Error(result.error || `Gagal memulai workflow (HTTP ${response.status})`);
                }
            } catch (error) {
                 console.error("Workflow Start Error:", error);
                alert('Error: Gagal memulai proses update stok. ' + error.message);
                 // --- UI Feedback End (on error) ---
                workflowStartBtn.textContent = originalText;
                // Re-evaluate button state
                toggleWorkflowStartButton();
            }
            // No 'finally' needed here as success navigates away.
        });
    }
});

