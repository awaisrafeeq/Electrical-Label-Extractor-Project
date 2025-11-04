/**
 * Electrical Label Extractor - Frontend Application
 * Handles file upload, processing, progress tracking, and label management
 */

// Global state
let currentJobId = null;
let statusPollInterval = null;

// DOM Elements
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const browseBtn = document.getElementById('browse-btn');
const fileInfo = document.getElementById('file-info');
const uploadSection = document.getElementById('upload-section');
const configSection = document.getElementById('config-section');
const processingSection = document.getElementById('processing-section');
const resultsSection = document.getElementById('results-section');
const newJobSection = document.getElementById('new-job-section');

// Configuration
const visionProviderSelect = document.getElementById('vision-provider');
const qualitySelect = document.getElementById('quality');
const startBtn = document.getElementById('start-btn');

// Processing
const progressFill = document.getElementById('progress-fill');
const progressText = document.getElementById('progress-text');
const currentPageSpan = document.getElementById('current-page');
const labelsCountSpan = document.getElementById('labels-count');
const processingSpeedSpan = document.getElementById('processing-speed');
const timeRemainingSpan = document.getElementById('time-remaining');
const activityText = document.getElementById('activity-text');
const activityIcon = document.getElementById('activity-icon');
const cancelBtn = document.getElementById('cancel-btn');

// Results
const totalLabelsSpan = document.getElementById('total-labels');
const labelsTbody = document.getElementById('labels-tbody');
const downloadExcelBtn = document.getElementById('download-excel-btn');

// New Job
const newJobBtn = document.getElementById('new-job-btn');

/**
 * Initialize application
 */
function init() {
    setupEventListeners();
    console.log('Application initialized');
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // File upload
    browseBtn.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', handleFileSelect);

    // Drag and drop
    dropZone.addEventListener('dragover', handleDragOver);
    dropZone.addEventListener('dragleave', handleDragLeave);
    dropZone.addEventListener('drop', handleDrop);
    dropZone.addEventListener('click', handleDropZoneClick);

    // Processing
    startBtn.addEventListener('click', startProcessing);

    // Add cancel button listener if it exists
    if (cancelBtn) {
        cancelBtn.addEventListener('click', cancelProcessing);
        console.log('Cancel button listener added');
    } else {
        console.error('Cancel button not found in DOM');
    }

    // Download
    downloadExcelBtn.addEventListener('click', downloadExcel);

    // New Job
    newJobBtn.addEventListener('click', resetApp);
}

/**
 * Drag and drop handlers
 */
function handleDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
    dropZone.classList.add('drag-over');
}

function handleDragLeave(e) {
    e.preventDefault();
    e.stopPropagation();
    dropZone.classList.remove('drag-over');
}

function handleDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    dropZone.classList.remove('drag-over');

    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
}

function handleDropZoneClick(e) {
    // Only trigger file input if clicking on drop zone itself or browse button
    // Ignore if already uploading
    if (dropZone.classList.contains('uploading')) {
        return;
    }

    // Check if clicking on browse button (handled by its own event listener)
    if (e.target.id === 'browse-btn' || e.target.closest('#browse-btn')) {
        return;
    }

    // Trigger file input for drop zone clicks
    if (e.target === dropZone || e.target.closest('.drop-zone')) {
        fileInput.click();
    }
}

function handleFileSelect(e) {
    const files = e.target.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
}

/**
 * Handle file upload
 */
async function handleFile(file) {
    // Validate file type
    if (!file.name.endsWith('.pdf')) {
        alert('Please upload a PDF file');
        return;
    }

    console.log('Uploading file:', file.name);

    // Show loading state and prevent further clicks
    dropZone.classList.add('uploading');
    dropZone.innerHTML = '<p class="loading">Uploading...</p>';

    try {
        // Create form data
        const formData = new FormData();
        formData.append('file', file);

        // Get configuration
        const config = {
            vision_provider: visionProviderSelect.value,
            pdf_dpi: parseInt(qualitySelect.value)
        };
        formData.append('config', JSON.stringify(config));

        // Upload file
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error('Upload failed');
        }

        const data = await response.json();
        console.log('Upload response:', data);

        // Store job ID
        currentJobId = data.job_id;

        // Show file info
        document.getElementById('filename').textContent = data.filename;
        document.getElementById('page-count').textContent = data.pages || 'Unknown';
        document.getElementById('job-id').textContent = data.job_id;

        fileInfo.style.display = 'block';

        // Reset drop zone and remove uploading state
        dropZone.classList.remove('uploading');
        resetDropZone();

        // Show configuration section
        configSection.style.display = 'block';

        // Scroll to config section
        configSection.scrollIntoView({ behavior: 'smooth' });

    } catch (error) {
        console.error('Upload error:', error);
        alert('Failed to upload file. Please try again.');
        dropZone.classList.remove('uploading');
        resetDropZone();
    }
}

/**
 * Reset drop zone
 */
function resetDropZone() {
    dropZone.classList.remove('uploading');
    dropZone.innerHTML = `
        <svg class="upload-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
        </svg>
        <p>Drag & Drop PDF Here</p>
        <p class="or">or</p>
        <button id="browse-btn" class="btn btn-primary">Browse Files</button>
    `;

    // Re-attach event listener to new browse button
    document.getElementById('browse-btn').addEventListener('click', () => fileInput.click());
}

/**
 * Start processing
 */
async function startProcessing() {
    if (!currentJobId) {
        alert('No file uploaded');
        return;
    }

    console.log('Starting processing for job:', currentJobId);

    try {
        // Start processing
        const response = await fetch(`/api/process/${currentJobId}`, {
            method: 'POST'
        });

        if (!response.ok) {
            throw new Error('Failed to start processing');
        }

        const data = await response.json();
        console.log('Processing started:', data);

        // Show processing section
        processingSection.style.display = 'block';

        // Scroll to processing section
        processingSection.scrollIntoView({ behavior: 'smooth' });

        // Start polling for status
        startStatusPolling();

    } catch (error) {
        console.error('Processing error:', error);
        alert('Failed to start processing. Please try again.');
    }
}

/**
 * Cancel processing
 */
async function cancelProcessing() {
    if (!currentJobId || !confirm('Are you sure you want to stop processing? You can still download partial results.')) {
        return;
    }

    try {
        cancelBtn.disabled = true;
        const originalText = cancelBtn.innerHTML;
        cancelBtn.innerHTML = '<span>Cancelling...</span>';

        const response = await fetch(`/api/cancel/${currentJobId}`, {
            method: 'POST'
        });

        if (!response.ok) {
            throw new Error('Failed to cancel');
        }

        const data = await response.json();
        console.log('Cancel requested:', data);

    } catch (error) {
        console.error('Cancel error:', error);
        alert('Failed to cancel processing');
        cancelBtn.disabled = false;
        cancelBtn.innerHTML = originalText;
    }
}

/**
 * Start status polling
 */
function startStatusPolling() {
    // Clear any existing interval
    if (statusPollInterval) {
        clearInterval(statusPollInterval);
    }

    // Poll every 2 seconds
    statusPollInterval = setInterval(checkStatus, 2000);

    // Check immediately
    checkStatus();
}

/**
 * Stop status polling
 */
function stopStatusPolling() {
    if (statusPollInterval) {
        clearInterval(statusPollInterval);
        statusPollInterval = null;
    }
}

/**
 * Check job status
 */
async function checkStatus() {
    if (!currentJobId) {
        stopStatusPolling();
        return;
    }

    try {
        const response = await fetch(`/api/status/${currentJobId}`);

        if (!response.ok) {
            throw new Error('Failed to get status');
        }

        const status = await response.json();
        console.log('Status:', status);

        // Update UI
        updateProgressUI(status);

        // Check if completed, cancelled, or failed
        if (status.status === 'completed') {
            stopStatusPolling();
            await loadLabels();
        } else if (status.status === 'cancelled') {
            stopStatusPolling();
            await loadLabels('cancelled');
        } else if (status.status === 'failed') {
            stopStatusPolling();
            showError(status.error || 'Processing failed');
        }

    } catch (error) {
        console.error('Status check error:', error);
    }
}

/**
 * Update progress UI
 */
function updateProgressUI(status) {
    console.log('Updating progress UI with status:', status);

    // Update progress bar
    const progress = status.progress_percent || 0;
    if (progressFill) {
        progressFill.style.width = `${progress}%`;
    }

    // Update progress text
    if (progressText) {
        progressText.textContent = getProgressText(status);
    }

    // Update stats
    if (currentPageSpan) {
        currentPageSpan.textContent = status.current_page || '-';
    }
    if (labelsCountSpan) {
        labelsCountSpan.textContent = status.labels_found || 0;
    }

    // Update activity status
    if (activityText && status.current_activity) {
        activityText.textContent = status.current_activity;
        console.log('Updated activity text:', status.current_activity);
    }

    // Update processing speed
    if (processingSpeedSpan) {
        if (status.processing_speed) {
            processingSpeedSpan.textContent = status.processing_speed.toFixed(1);
            console.log('Updated speed:', status.processing_speed);
        } else {
            processingSpeedSpan.textContent = '-';
        }
    }

    // Update time remaining
    if (timeRemainingSpan) {
        if (status.estimated_time_remaining) {
            const minutes = Math.floor(status.estimated_time_remaining / 60);
            const seconds = status.estimated_time_remaining % 60;
            timeRemainingSpan.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
            console.log('Updated time remaining:', status.estimated_time_remaining);
        } else {
            timeRemainingSpan.textContent = '-';
        }
    }

    // Update icon and cancel button based on status
    if (status.status === 'cancelled') {
        if (activityIcon) {
            activityIcon.textContent = '⏸️';
            activityIcon.style.animation = 'none';
        }
        if (cancelBtn) {
            cancelBtn.style.display = 'none';
        }
    } else if (status.status === 'processing') {
        if (activityIcon) {
            activityIcon.textContent = '🔄';
            activityIcon.style.animation = 'spin 2s linear infinite';
        }
        if (cancelBtn) {
            cancelBtn.style.display = 'block';
            console.log('Cancel button should be visible');
        }
    } else if (status.status === 'completed') {
        if (activityIcon) {
            activityIcon.textContent = '✅';
            activityIcon.style.animation = 'none';
        }
        if (cancelBtn) {
            cancelBtn.style.display = 'none';
        }
    }
}

/**
 * Get progress text
 */
function getProgressText(status) {
    if (status.status === 'uploaded') {
        return 'Waiting to start...';
    } else if (status.status === 'processing') {
        const currentPage = status.current_page || 0;
        const totalPages = status.pages || 0;
        return `Processing page ${currentPage} of ${totalPages}...`;
    } else if (status.status === 'completed') {
        return 'Processing complete!';
    } else if (status.status === 'cancelled') {
        return 'Processing cancelled - Partial results available';
    } else if (status.status === 'failed') {
        return 'Processing failed';
    }
    return 'Unknown status';
}

/**
 * Format status text
 */
function formatStatus(status) {
    const statusMap = {
        'uploaded': 'Queued',
        'processing': 'Processing',
        'completed': 'Completed',
        'failed': 'Failed'
    };
    return statusMap[status] || status;
}

/**
 * Load labels
 */
async function loadLabels(status = 'completed') {
    try {
        const response = await fetch(`/api/labels/${currentJobId}`);

        if (!response.ok) {
            throw new Error('Failed to load labels');
        }

        const data = await response.json();
        console.log('Labels:', data);

        // Display labels
        displayLabels(data.labels, status);

        // Show results section
        resultsSection.style.display = 'block';
        newJobSection.style.display = 'block';

        // Scroll to results
        resultsSection.scrollIntoView({ behavior: 'smooth' });

    } catch (error) {
        console.error('Load labels error:', error);
        showError('Failed to load labels');
    }
}

/**
 * Display labels in table
 */
function displayLabels(labels, status = 'completed') {
    // Update count
    totalLabelsSpan.textContent = labels.length;

    // Show warning for partial results
    if (status === 'cancelled') {
        const warning = document.createElement('div');
        warning.className = 'warning-message';
        warning.style.cssText = 'background: #fff3cd; border: 1px solid #ffc107; color: #856404; padding: 1rem; margin-bottom: 1rem; border-radius: 8px;';
        warning.innerHTML = `
            <strong>⚠️ Partial Results:</strong> Processing was cancelled.
            The results shown below are from the pages that were processed before cancellation.
        `;
        resultsSection.insertBefore(warning, resultsSection.querySelector('.results-header'));
    }

    // Clear table
    labelsTbody.innerHTML = '';

    // Add rows
    labels.forEach((label, index) => {
        const row = createLabelRow(label, index);
        labelsTbody.appendChild(row);
    });
}

/**
 * Create label table row
 */
function createLabelRow(label, index) {
    const row = document.createElement('tr');
    row.dataset.labelId = index;

    // Get image page number (default to 1 if not specified)
    const imagePage = label.image_page || 1;

    // Use cropped image if available, otherwise use full page image
    const croppedUrl = `/api/cropped-label/${currentJobId}/${index}`;
    const pageUrl = `/api/page-image/${currentJobId}/${imagePage}`;
    const annotatedUrl = `/api/annotated-image/${currentJobId}/${imagePage}`;
    const imageUrl = label.has_bbox ? croppedUrl : pageUrl;
    const fullImageUrl = label.has_bbox ? annotatedUrl : pageUrl;

    console.log(`Label ${index + 1}: page=${imagePage}, cropped=${croppedUrl}, annotated=${annotatedUrl}`);

    row.innerHTML = `
        <td>${index + 1}</td>
        <td>
            <div class="image-preview-container">
                <img
                    src="${imageUrl}"
                    alt="Label ${index + 1} (Page ${imagePage})"
                    class="label-thumbnail"
                    data-full-url="${fullImageUrl}"
                    data-page="${imagePage}"
                    data-label-tag="${escapeHtml(label.device_tag || '')}"
                    onerror="this.src='${pageUrl}'; this.classList.add('fallback');"
                >
                ${label.has_bbox ? '<span class="bbox-indicator" title="Bounding box available">📍</span>' : ''}
            </div>
        </td>
        <td class="editable" data-field="equipment_type">${escapeHtml(label.equipment_type || '')}</td>
        <td class="editable" data-field="device_tag">${escapeHtml(label.device_tag || '')}</td>
        <td class="editable" data-field="fed_from">${escapeHtml(label.fed_from || label.primary_from || '')}</td>
        <td class="editable" data-field="primary_from">${escapeHtml(label.primary_from || '')}</td>
        <td class="editable" data-field="specs">${escapeHtml(label.specs || '')}</td>
        <td>${label.is_spare ? 'YES' : 'NO'}</td>
        <td>
            <button class="btn action-btn btn-edit" onclick="editLabel(${index})">Edit</button>
            <button class="btn action-btn btn-delete" onclick="deleteLabel(${index})">Delete</button>
        </td>
    `;

    // Add click handler for image
    const img = row.querySelector('.label-thumbnail');
    img.addEventListener('click', function() {
        const fullUrl = this.getAttribute('data-full-url');
        const page = this.getAttribute('data-page');
        const tag = this.getAttribute('data-label-tag');
        const hasBbox = label.has_bbox;
        openImageModal(fullUrl, `Page ${page} - ${tag}${hasBbox ? ' (with bounding box #' + (index + 1) + ')' : ''}`);
    });

    // Add double-click edit functionality
    row.querySelectorAll('.editable').forEach(cell => {
        cell.addEventListener('dblclick', () => makeEditable(cell, index));
    });

    return row;
}

/**
 * Make cell editable
 */
function makeEditable(cell, labelId) {
    const field = cell.dataset.field;
    const currentValue = cell.textContent;

    // Create input
    const input = document.createElement('input');
    input.type = 'text';
    input.value = currentValue;
    input.className = 'edit-input';

    // Replace cell content
    cell.textContent = '';
    cell.appendChild(input);
    input.focus();

    // Handle save on blur or Enter
    const saveEdit = async () => {
        const newValue = input.value;

        if (newValue !== currentValue) {
            await updateLabelField(labelId, field, newValue);
        }

        cell.textContent = newValue;
    };

    input.addEventListener('blur', saveEdit);
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            saveEdit();
        }
    });
}

/**
 * Update label field
 */
async function updateLabelField(labelId, field, value) {
    try {
        const update = { [field]: value };

        const response = await fetch(`/api/labels/${currentJobId}/${labelId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(update)
        });

        if (!response.ok) {
            throw new Error('Failed to update label');
        }

        console.log(`Updated label ${labelId}, field ${field} to ${value}`);

    } catch (error) {
        console.error('Update error:', error);
        alert('Failed to update label');
    }
}

/**
 * Edit label (button click)
 */
function editLabel(labelId) {
    const row = document.querySelector(`tr[data-label-id="${labelId}"]`);
    const editableCells = row.querySelectorAll('.editable');

    // Make first editable cell editable
    if (editableCells.length > 0) {
        makeEditable(editableCells[0], labelId);
    }
}

/**
 * Delete label
 */
async function deleteLabel(labelId) {
    if (!confirm('Are you sure you want to delete this label?')) {
        return;
    }

    try {
        const response = await fetch(`/api/labels/${currentJobId}/${labelId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error('Failed to delete label');
        }

        console.log(`Deleted label ${labelId}`);

        // Reload labels
        await loadLabels();

    } catch (error) {
        console.error('Delete error:', error);
        alert('Failed to delete label');
    }
}

/**
 * Download Excel
 */
async function downloadExcel() {
    if (!currentJobId) {
        alert('No job to download');
        return;
    }

    try {
        // Open download URL in new window
        window.location.href = `/api/export/${currentJobId}`;

    } catch (error) {
        console.error('Download error:', error);
        alert('Failed to download Excel file');
    }
}

/**
 * Reset app for new job
 */
function resetApp() {
    // Reset state
    currentJobId = null;
    stopStatusPolling();

    // Reset UI
    fileInfo.style.display = 'none';
    configSection.style.display = 'none';
    processingSection.style.display = 'none';
    resultsSection.style.display = 'none';
    newJobSection.style.display = 'none';

    // Reset progress
    progressFill.style.width = '0%';
    progressText.textContent = 'Initializing...';
    currentPageSpan.textContent = '-';
    labelsCountSpan.textContent = '0';
    processingSpeedSpan.textContent = '-';
    timeRemainingSpan.textContent = '-';
    activityText.textContent = 'Initializing...';
    activityIcon.textContent = '🔄';
    activityIcon.style.animation = '';
    cancelBtn.style.display = 'block';
    cancelBtn.disabled = false;
    cancelBtn.innerHTML = `
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
            <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/>
            <path d="M4.646 4.646a.5.5 0 0 1 .708 0L8 7.293l2.646-2.647a.5.5 0 0 1 .708.708L8.707 8l2.647 2.646a.5.5 0 0 1-.708.708L8 8.707l-2.646 2.647a.5.5 0 0 1-.708-.708L7.293 8 4.646 5.354a.5.5 0 0 1 0-.708z"/>
        </svg>
        Stop Processing
    `;

    // Reset file input
    fileInput.value = '';

    // Reset drop zone
    resetDropZone();

    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

/**
 * Show error message
 */
function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.textContent = `Error: ${message}`;

    processingSection.insertBefore(errorDiv, processingSection.firstChild);

    // Remove after 5 seconds
    setTimeout(() => {
        errorDiv.remove();
    }, 5000);
}

/**
 * Escape HTML
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Open image modal
 */
function openImageModal(imageUrl, caption) {
    const modal = document.getElementById('image-modal');
    const modalImage = document.getElementById('modal-image');
    const modalCaption = document.getElementById('modal-caption');

    modal.classList.add('active');
    modalImage.src = imageUrl;
    modalCaption.textContent = caption;

    // Close on escape key
    document.addEventListener('keydown', handleModalEscape);
}

/**
 * Close image modal
 */
function closeImageModal() {
    const modal = document.getElementById('image-modal');
    modal.classList.remove('active');

    // Remove escape key listener
    document.removeEventListener('keydown', handleModalEscape);
}

/**
 * Handle escape key to close modal
 */
function handleModalEscape(e) {
    if (e.key === 'Escape') {
        closeImageModal();
    }
}

// Close modal when clicking outside the image
document.addEventListener('click', (e) => {
    const modal = document.getElementById('image-modal');
    if (e.target === modal) {
        closeImageModal();
    }
});

// Initialize app when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
