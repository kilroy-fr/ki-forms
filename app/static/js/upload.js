document.addEventListener("DOMContentLoaded", function () {
    const formSelect = document.getElementById("formSelect");
    const thumbnail = document.getElementById("formThumbnail");
    const dropZone = document.getElementById("dropZone");
    const fileInput = document.getElementById("fileInput");
    const fileList = document.getElementById("fileList");
    const submitBtn = document.getElementById("submitBtn");
    const uploadForm = document.getElementById("uploadForm");
    const processingInfo = document.getElementById("processingInfo");

    let filesSelected = false;

    // Formular-Dropdown: Thumbnail laden und Form-Action setzen
    if (formSelect) {
        formSelect.addEventListener("change", function () {
            const formId = this.value;
            if (formId) {
                thumbnail.src = "/form/" + formId + "/thumbnail";
                thumbnail.classList.remove("d-none");
                uploadForm.action = "/form/" + formId + "/process";
            } else {
                thumbnail.classList.add("d-none");
                thumbnail.src = "";
                uploadForm.action = "";
            }
            updateSubmitState();
        });

        // Initial: Falls Formular vorausgewaehlt (z.B. nach Redirect)
        if (formSelect.value) {
            thumbnail.src = "/form/" + formSelect.value + "/thumbnail";
            thumbnail.classList.remove("d-none");
            uploadForm.action = "/form/" + formSelect.value + "/process";
        }
    }

    function updateSubmitState() {
        var formChosen = formSelect && formSelect.value;
        submitBtn.disabled = !(formChosen && filesSelected);
    }

    // Klick auf Drop-Zone oeffnet Dateiauswahl
    dropZone.addEventListener("click", function () {
        fileInput.click();
    });

    // Drag & Drop Events
    dropZone.addEventListener("dragover", function (e) {
        e.preventDefault();
        dropZone.classList.add("drag-over");
    });

    dropZone.addEventListener("dragleave", function () {
        dropZone.classList.remove("drag-over");
    });

    dropZone.addEventListener("drop", function (e) {
        e.preventDefault();
        dropZone.classList.remove("drag-over");

        var files = e.dataTransfer.files;
        if (files.length > 0) {
            fileInput.files = files;
            updateFileList();
        }
    });

    // Dateiauswahl ueber Dialog
    fileInput.addEventListener("change", function () {
        updateFileList();
    });

    function updateFileList() {
        fileList.innerHTML = "";
        var files = fileInput.files;

        if (files.length === 0) {
            filesSelected = false;
            updateSubmitState();
            return;
        }

        for (var i = 0; i < files.length; i++) {
            var file = files[i];
            var sizeMB = (file.size / (1024 * 1024)).toFixed(1);
            var item = document.createElement("div");
            item.className = "d-flex align-items-center p-2 mb-1 bg-light rounded";
            item.innerHTML =
                '<i class="bi bi-file-earmark-pdf text-danger me-2"></i>' +
                '<span class="flex-grow-1">' + file.name + "</span>" +
                '<span class="text-muted small">' + sizeMB + " MB</span>";
            fileList.appendChild(item);
        }

        filesSelected = true;
        updateSubmitState();
    }

    // Formular absenden: Ladeindikator zeigen
    uploadForm.addEventListener("submit", function (e) {
        if (!formSelect || !formSelect.value) {
            e.preventDefault();
            return;
        }
        submitBtn.disabled = true;
        submitBtn.innerHTML =
            '<span class="spinner-border spinner-border-sm me-2"></span>Wird verarbeitet...';
        dropZone.classList.add("d-none");
        fileList.classList.add("d-none");
        processingInfo.classList.remove("d-none");
    });
});
