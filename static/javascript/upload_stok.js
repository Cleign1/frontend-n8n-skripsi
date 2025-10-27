// static/javascript/upload_stok.js

document.addEventListener('DOMContentLoaded', function() {

    // --- UI ELEMENTS (Using new R2 IDs) ---
    const uploadR2Btn = document.getElementById('upload-r2-btn'); // Matched HTML ID
    const workflowStartBtn = document.getElementById('start-update-btn');
    const fileInput = document.getElementById('file-input');
    const r2DatePicker = document.getElementById('r2-date-picker'); // Matched HTML ID
    const workflowDatePicker = document.getElementById('workflow-date-picker');
    const workflowDateMessage = document.getElementById('workflow-date-message');
    const r2DateMessage = document.getElementById('r2-date-message'); // Matched HTML ID

    // --- UTILITY FUNCTIONS ---
    function getFormattedDate(datePicker) {
        const selectedDate = datePicker.value;
        if (!selectedDate) {
            return null;
        }
        // Returns date string in YYYYMMDD format as needed by backend
        const formattedDate = selectedDate.replace(/-/g, '');
        return formattedDate;
    }

    // --- TOGGLE FUNCTIONS ---

    /**
     * Toggles the state of the main workflow button (Start Update Stok).
     */
    function toggleWorkflowStartButton() {
        if (!workflowStartBtn || !workflowDatePicker) return;
        const selectedDate = workflowDatePicker.value;
        const isDateSelected = !!selectedDate;
        workflowStartBtn.disabled = !isDateSelected;
        workflowDateMessage.classList.toggle('hidden', isDateSelected);
    }

    /**
     * Toggles the state of the R2 upload button.
     */
    function toggleR2UploadButton() { // Function name updated
        // Use R2 variables
        if (!uploadR2Btn || !r2DatePicker) return;

        const isFilePresent = !!selectedFileFromServer;
        const isDateSelected = !!r2DatePicker.value;
        const shouldEnable = isFilePresent && isDateSelected;

        uploadR2Btn.disabled = !shouldEnable;

        // Use R2 variables
        r2DateMessage.classList.toggle('hidden', !isFilePresent || isDateSelected);

        // Update button text dynamically
        if (isFilePresent) {
             uploadR2Btn.textContent = `Upload ${selectedFileFromServer} ke R2`; // Updated text
        } else {
             uploadR2Btn.textContent = `Upload File ke R2`; // Updated default text
        }
    }


    // --- INITIAL STATE SETUP ---
    toggleWorkflowStartButton();
    toggleR2UploadButton(); // Call updated function name

    // --- EVENT LISTENERS (Using R2 variables) ---

    if (workflowDatePicker) {
        workflowDatePicker.addEventListener('change', toggleWorkflowStartButton);
        workflowDatePicker.addEventListener('input', toggleWorkflowStartButton);
    }

    // Listen for R2 date changes
    if (r2DatePicker) {
        r2DatePicker.addEventListener('change', toggleR2UploadButton); // Call updated function name
        r2DatePicker.addEventListener('input', toggleR2UploadButton); // Call updated function name
    }


    // 3. Upload to R2 Button Handler (Upload to R2)
    if (uploadR2Btn) {
        uploadR2Btn.addEventListener('click', async function () {

            if (!selectedFileFromServer) {
                console.error("Upload Error: No file selected on server.");
                alert("Kesalahan: Tidak ada file di server untuk diupload.");
                return;
            }

            // Use R2 variable
            const formattedDate = getFormattedDate(r2DatePicker);

            if (!formattedDate) {
                // Use R2 variable
                r2DateMessage.classList.remove('hidden');
                console.error("Upload Error: Date not selected for R2 upload.");
                alert("Pilih tanggal untuk penamaan file di R2!"); // Updated text
                return;
            }
             // Use R2 variable
            r2DateMessage.classList.add('hidden');

            // --- UI Feedback Start ---
            const originalText = uploadR2Btn.textContent;
            uploadR2Btn.disabled = true;
            uploadR2Btn.textContent = 'Memulai Upload Task...';

            const formData = new FormData();
            formData.append('server_filename', selectedFileFromServer);
            formData.append('selected_date', formattedDate);

            try {
                // Call the backend endpoint to start the R2 upload task
                const response = await fetch('/upload/start_r2_upload', {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();

                if (response.ok) {
                    // Success: Task started
                    alert(result.message + ` (Task ID: ${result.celery_task_id}). Anda bisa memonitor di halaman Tasks.`);
                } else {
                    // Failure: Error starting task
                    throw new Error(result.error || 'Gagal memulai R2 upload task.');
                }

            } catch (error) {
                console.error("R2 Upload Task Start Error:", error);
                alert('Error memulai task: ' + error.message);
            } finally {
                // --- UI Feedback End ---
                uploadR2Btn.textContent = originalText;
                // Re-evaluate button state
                toggleR2UploadButton(); // Call updated function name
            }
        });
    }

    // 4. Start Update Stock Workflow Button Handler (Remains the same)
    if (workflowStartBtn) {
         workflowStartBtn.addEventListener('click', async function() {
            const selectedDate = getFormattedDate(workflowDatePicker);
            if (!selectedDate) {
                workflowDateMessage.classList.remove('hidden');
                alert("Pilih tanggal update terlebih dahulu!");
                return;
            }
            workflowDateMessage.classList.add('hidden');

            const originalText = workflowStartBtn.textContent;
            workflowStartBtn.disabled = true;
            workflowStartBtn.textContent = 'Memulai...';

            try {
                const response = await fetch('/api/workflow/start', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ date: selectedDate, workflow_type: 'update' })
                });

                const result = await response.json();

                if (response.ok) {
                    window.location.href = `/workflow/update/${result.task_id}`;
                } else {
                    throw new Error(result.error || `Gagal memulai workflow (HTTP ${response.status})`);
                }
            } catch (error) {
                 console.error("Workflow Start Error:", error);
                alert('Error: Gagal memulai proses update stok. ' + error.message);
                workflowStartBtn.textContent = originalText;
                toggleWorkflowStartButton();
            }
        });
    }
}); // End DOMContentLoaded