document.addEventListener("DOMContentLoaded", function () {
    const formSelect = document.getElementById("formSelect");
    const thumbnail = document.getElementById("formThumbnail");
    const thumbnailContainer = document.getElementById("thumbnailContainer");
    const dropZone = document.getElementById("dropZone");
    const fileInput = document.getElementById("fileInput");
    const fileList = document.getElementById("fileList");
    const submitBtn = document.getElementById("submitBtn");
    const uploadForm = document.getElementById("uploadForm");
    const spinnerOverlay = document.getElementById("spinnerOverlay");
    const s0050StandaloneSection = document.getElementById("s0050StandaloneSection");

    let filesSelected = false;
    let selectedFiles = []; // Array zum Speichern ausgewählter Dateien

    // Formular-Dropdown: Thumbnail laden und Form-Action setzen
    if (formSelect) {
        formSelect.addEventListener("change", function () {
            const formId = this.value;
            if (formId) {
                thumbnail.src = "/form/" + formId + "/thumbnail";
                thumbnailContainer.classList.remove("d-none");
                uploadForm.action = "/form/" + formId + "/process";

                // S0050-Standalone-Bereich anzeigen, wenn S0050 ausgewählt ist
                if (s0050StandaloneSection) {
                    if (formId === "S0050") {
                        s0050StandaloneSection.classList.remove("d-none");
                    } else {
                        s0050StandaloneSection.classList.add("d-none");
                    }
                }

                // Ollama-Warmup starten, sobald ein Formular ausgewählt wird
                fetch('/api/warmup', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                })
                .then(response => {
                    if (response.ok) {
                        console.log('Ollama Warmup gestartet');
                    }
                })
                .catch(error => {
                    console.warn('Warmup-Request fehlgeschlagen:', error);
                });
            } else {
                thumbnailContainer.classList.add("d-none");
                thumbnail.src = "";
                uploadForm.action = "";
                if (s0050StandaloneSection) {
                    s0050StandaloneSection.classList.add("d-none");
                }
            }
            updateSubmitState();
        });

        // Initial: Falls Formular vorausgewaehlt (z.B. nach Redirect)
        if (formSelect.value) {
            thumbnail.src = "/form/" + formSelect.value + "/thumbnail";
            thumbnailContainer.classList.remove("d-none");
            uploadForm.action = "/form/" + formSelect.value + "/process";

            // S0050-Standalone-Bereich initial anzeigen, wenn S0050 vorausgewählt
            if (s0050StandaloneSection && formSelect.value === "S0050") {
                s0050StandaloneSection.classList.remove("d-none");
            }
        }
    }

    function updateSubmitState() {
        var formChosen = formSelect && formSelect.value;
        submitBtn.disabled = !(formChosen && filesSelected);
    }

    // Verhindere Event-Bubbling vom fileInput
    fileInput.addEventListener("click", function (e) {
        e.stopPropagation();
    });

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
            addFiles(files);
        }
    });

    // Dateiauswahl ueber Dialog
    fileInput.addEventListener("change", function () {
        if (fileInput.files.length > 0) {
            addFiles(fileInput.files);
        }
    });

    // Dateien zum Array hinzufügen
    function addFiles(files) {
        for (var i = 0; i < files.length; i++) {
            selectedFiles.push(files[i]);
        }
        updateFileList();
    }

    // Datei aus dem Array entfernen
    function removeFile(index) {
        selectedFiles.splice(index, 1);
        updateFileList();
    }

    function updateFileList() {
        fileList.innerHTML = "";

        if (selectedFiles.length === 0) {
            filesSelected = false;
            updateSubmitState();
            return;
        }

        for (var i = 0; i < selectedFiles.length; i++) {
            var file = selectedFiles[i];
            var sizeMB = (file.size / (1024 * 1024)).toFixed(1);
            var item = document.createElement("div");
            item.className = "file-list-item";
            item.innerHTML =
                '<div class="file-list-icon">' +
                '<i class="bi bi-file-earmark-pdf"></i>' +
                '</div>' +
                '<div class="file-list-name" title="' + file.name + '">' + file.name + '</div>' +
                '<div class="file-list-size">' + sizeMB + ' MB</div>' +
                '<div class="file-list-delete">' +
                '<button type="button" class="btn btn-sm btn-outline-danger border-0" data-index="' + i + '" title="Datei entfernen">' +
                '<i class="bi bi-trash"></i>' +
                '</button>' +
                '</div>';
            fileList.appendChild(item);
        }

        // Event-Listener für Lösch-Buttons hinzufügen
        var deleteButtons = fileList.querySelectorAll("button[data-index]");
        deleteButtons.forEach(function (btn) {
            btn.addEventListener("click", function () {
                var index = parseInt(this.getAttribute("data-index"));
                removeFile(index);
            });
        });

        filesSelected = true;
        updateSubmitState();
    }

    // Formular absenden: Ladeindikator zeigen
    uploadForm.addEventListener("submit", function (e) {
        e.preventDefault();

        if (!formSelect || !formSelect.value) {
            return;
        }

        if (selectedFiles.length === 0) {
            return;
        }

        // FormData mit ausgewählten Dateien erstellen
        var formData = new FormData();
        for (var i = 0; i < selectedFiles.length; i++) {
            formData.append("files", selectedFiles[i]);
        }

        // Spinner Overlay anzeigen
        if (spinnerOverlay) {
            spinnerOverlay.classList.remove("d-none");
        }

        submitBtn.disabled = true;

        // AJAX-Request senden
        fetch(uploadForm.action, {
            method: "POST",
            body: formData
        })
        .then(function(response) {
            // Overlay ausblenden vor Redirect oder neuem Seiteninhalt
            if (spinnerOverlay) {
                spinnerOverlay.classList.add("d-none");
            }

            if (response.redirected) {
                window.location.href = response.url;
            } else {
                return response.text().then(function(text) {
                    document.open();
                    document.write(text);
                    document.close();
                });
            }
        })
        .catch(function(error) {
            console.error("Fehler:", error);
            alert("Ein Fehler ist aufgetreten. Bitte versuchen Sie es erneut.");
            submitBtn.disabled = false;
            if (spinnerOverlay) {
                spinnerOverlay.classList.add("d-none");
            }
        });
    });
});
