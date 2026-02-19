/**
 * Absender-Daten Verwaltung
 * Verwaltet die Eingabe, Speicherung und Anzeige von bis zu 5 Ärzten
 */

// DOM Elemente
const editSenderBtn = document.getElementById('editSenderBtn');
const senderModal = document.getElementById('senderModal');
const closeSenderModal = document.getElementById('closeSenderModal');
const cancelSenderBtn = document.getElementById('cancelSenderBtn');
const senderDataForm = document.getElementById('senderDataForm');
const senderDataDisplay = document.getElementById('senderDataDisplay');
const prevDoctorBtn = document.getElementById('prevDoctorBtn');
const nextDoctorBtn = document.getElementById('nextDoctorBtn');
const currentDoctorIndexEl = document.getElementById('currentDoctorIndex');
const totalDoctorsEl = document.getElementById('totalDoctors');
const activeDoctorBadge = document.getElementById('activeDoctorBadge');
const setActiveDoctorBtn = document.getElementById('setActiveDoctorBtn');

// Globale Variablen
const MAX_DOCTORS = 5;
let doctors = []; // Array von bis zu 5 Ärzten
let currentDoctorIndex = 0; // Aktuell angezeigter Arzt im Modal (0-4)
let activeDoctorIndex = 0;  // Index des Arztes, der in Formularen verwendet wird

/**
 * Initialisiert leere Ärzte-Slots
 */
function initializeEmptyDoctors() {
    const emptyDoctor = {
        anrede: '',
        titel: '',
        vorname: '',
        name: '',
        fachrichtung: '',
        praxis: '',
        institutionskennzeichen: '',
        strasse: '',
        hausnummer: '',
        plz: '',
        ort: '',
        telefon: '',
        email: '',
        kontoinhaber: '',
        iban: '',
        bic: '',
        kreditinstitut: ''
    };
    return Array(MAX_DOCTORS).fill(null).map(() => ({ ...emptyDoctor }));
}

/**
 * Öffnet das Modal zur Bearbeitung der Absender-Daten
 */
async function openSenderModal() {
    // Lade alle Ärzte
    await loadDoctors();

    // Zeige den aktuellen Arzt
    loadDoctorIntoForm(currentDoctorIndex);

    // Aktualisiere Navigation
    updateNavigation();

    senderModal.classList.remove('d-none');
}

/**
 * Schließt das Modal
 */
function closeSenderModalHandler() {
    // Speichere aktuellen Arzt vor dem Schließen
    saveCurrentDoctorToArray();

    senderModal.classList.add('d-none');
}

/**
 * Lädt alle Ärzte vom Backend
 */
async function loadDoctors() {
    try {
        const response = await fetch('/api/sender-data', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
        });

        if (!response.ok) {
            throw new Error('Fehler beim Laden der Daten');
        }

        const data = await response.json();

        // Aktiven Arzt-Index laden
        activeDoctorIndex = typeof data.active_doctor_index === 'number' ? data.active_doctor_index : 0;

        // Initialisiere mit leeren Ärzten
        doctors = initializeEmptyDoctors();

        // Überschreibe mit gespeicherten Daten
        if (data.doctors && Array.isArray(data.doctors)) {
            data.doctors.forEach((doctor, index) => {
                if (index < MAX_DOCTORS) {
                    doctors[index] = { ...doctors[index], ...doctor };
                }
            });
        }

        // Fülle neue Ärzte (2-5) mit Praxis-Daten vom ersten Arzt vor
        prefillPracticeDataForNewDoctors();
    } catch (error) {
        console.error('Fehler beim Laden:', error);
        doctors = initializeEmptyDoctors();
    }
}

/**
 * Füllt die Praxis-Daten (ab "praxis") für leere Ärzte mit den Daten vom ersten Arzt vor
 */
function prefillPracticeDataForNewDoctors() {
    if (!doctors || doctors.length === 0) return;

    const firstDoctor = doctors[0];

    // Felder, die vom ersten Arzt übernommen werden sollen (ab "praxis")
    const practiceFields = [
        'praxis',
        'institutionskennzeichen',
        'strasse',
        'hausnummer',
        'plz',
        'ort',
        'telefon',
        'email',
        'kontoinhaber',
        'iban',
        'bic',
        'kreditinstitut'
    ];

    // Für Ärzte 2-5
    for (let i = 1; i < MAX_DOCTORS; i++) {
        const doctor = doctors[i];

        // Prüfe ob der Arzt leer ist (keine persönlichen Daten)
        const isEmpty = !doctor.vorname && !doctor.name && !doctor.anrede && !doctor.titel && !doctor.fachrichtung;

        // Wenn leer, übernehme Praxis-Daten vom ersten Arzt
        if (isEmpty) {
            practiceFields.forEach(field => {
                if (firstDoctor[field]) {
                    doctor[field] = firstDoctor[field];
                }
            });
        }
    }
}

/**
 * Lädt einen bestimmten Arzt ins Formular
 */
function loadDoctorIntoForm(index) {
    if (index < 0 || index >= MAX_DOCTORS) return;

    const doctor = doctors[index];
    Object.keys(doctor).forEach(key => {
        const input = document.getElementById(key);
        if (input) {
            input.value = doctor[key] || '';
        }
    });
}

/**
 * Speichert den aktuellen Formular-Inhalt in das Ärzte-Array
 */
function saveCurrentDoctorToArray() {
    const formData = new FormData(senderDataForm);
    const doctorData = {};

    formData.forEach((value, key) => {
        doctorData[key] = value.trim();
    });

    doctors[currentDoctorIndex] = doctorData;
}

/**
 * Wechselt zu einem anderen Arzt
 */
function switchDoctor(newIndex) {
    if (newIndex < 0 || newIndex >= MAX_DOCTORS) return;

    // Speichere aktuellen Arzt
    saveCurrentDoctorToArray();

    // Wechsle Index
    currentDoctorIndex = newIndex;

    // Lade neuen Arzt
    loadDoctorIntoForm(currentDoctorIndex);

    // Aktualisiere Navigation
    updateNavigation();
}

/**
 * Aktualisiert die Navigation-Buttons, Anzeige und Aktiv-Indikator
 */
function updateNavigation() {
    // Aktualisiere Anzeige
    currentDoctorIndexEl.textContent = currentDoctorIndex + 1;
    totalDoctorsEl.textContent = MAX_DOCTORS;

    // Prev-Button aktivieren/deaktivieren
    prevDoctorBtn.disabled = currentDoctorIndex === 0;

    // Next-Button aktivieren/deaktivieren
    nextDoctorBtn.disabled = currentDoctorIndex === MAX_DOCTORS - 1;

    // Aktiv-Badge und Button aktualisieren
    const isActive = currentDoctorIndex === activeDoctorIndex;
    if (isActive) {
        activeDoctorBadge.classList.remove('d-none');
        setActiveDoctorBtn.disabled = true;
        setActiveDoctorBtn.innerHTML = '<i class="bi bi-star-fill"></i> Aktiver Arzt';
    } else {
        activeDoctorBadge.classList.add('d-none');
        setActiveDoctorBtn.disabled = false;
        setActiveDoctorBtn.innerHTML = '<i class="bi bi-star"></i> Als aktiven Arzt festlegen';
    }
}

/**
 * Setzt den aktuell angezeigten Arzt als aktiven Arzt
 */
async function setActiveDoctorHandler() {
    // Aktuellen Arzt zuerst im Array speichern
    saveCurrentDoctorToArray();

    // Aktiven Index setzen
    activeDoctorIndex = currentDoctorIndex;

    // Sofort speichern
    try {
        await saveDoctors();
        updateNavigation();
        console.log(`Arzt ${activeDoctorIndex + 1} als aktiver Arzt gesetzt`);
    } catch (error) {
        console.error('Fehler beim Setzen des aktiven Arztes:', error);
    }
}

/**
 * Füllt das Formular mit gespeicherten Daten (Legacy-Funktion)
 */
function fillForm(data) {
    Object.keys(data).forEach(key => {
        const input = document.getElementById(key);
        if (input) {
            input.value = data[key] || '';
        }
    });
}

/**
 * Speichert alle Ärzte im Backend
 */
async function saveDoctors() {
    try {
        // Speichere aktuellen Arzt vor dem Speichern
        saveCurrentDoctorToArray();

        // Filtere leere Ärzte (die keine Daten haben)
        const nonEmptyDoctors = doctors.filter(doctor => {
            return Object.values(doctor).some(value => value && value.trim() !== '');
        });

        const response = await fetch('/api/sender-data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ doctors: nonEmptyDoctors, active_doctor_index: activeDoctorIndex }),
        });

        if (!response.ok) {
            throw new Error('Fehler beim Speichern der Daten');
        }

        return await response.json();
    } catch (error) {
        console.error('Fehler beim Speichern:', error);
        alert('Fehler beim Speichern der Absender-Daten. Bitte versuchen Sie es erneut.');
        throw error;
    }
}

/**
 * Lädt die Absender-Daten vom Backend.
 * Gibt den aktiven Arzt zurück.
 */
async function getSenderData() {
    try {
        const response = await fetch('/api/sender-data', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
        });

        if (!response.ok) {
            throw new Error('Fehler beim Laden der Daten');
        }

        const data = await response.json();

        if (data.doctors && Array.isArray(data.doctors) && data.doctors.length > 0) {
            // Aktiven Arzt zurückgeben
            const idx = typeof data.active_doctor_index === 'number' ? data.active_doctor_index : 0;
            return data.doctors[idx] || data.doctors[0];
        }

        return null;
    } catch (error) {
        console.error('Fehler beim Laden:', error);
        return null;
    }
}

/**
 * Zeigt die gespeicherten Absender-Daten an (aktiver Arzt)
 */
async function displaySenderData() {
    const data = await getSenderData();

    if (!data) {
        senderDataDisplay.innerHTML = `
            <p class="text-muted text-center py-4">
                <i class="bi bi-person-badge fs-1 d-block mb-2"></i>
                Noch keine Absender-Daten hinterlegt
            </p>
        `;
        return;
    }

    // Erstelle HTML für die Anzeige (zeigt den aktiven Arzt)
    let html = '<div class="sender-data-content">';

    // Persönliche Daten
    if (data.anrede || data.titel || data.vorname || data.name) {
        const fullName = [data.anrede, data.titel, data.vorname, data.name]
            .filter(Boolean)
            .join(' ');
        html += `<p><strong class="sender-value">${fullName}</strong></p>`;
    }

    if (data.fachrichtung) {
        html += `<p class="sender-value text-muted">${data.fachrichtung}</p>`;
    }

    if (data.praxis) {
        html += `<p class="sender-value">${data.praxis}</p>`;
    }

    // Adresse
    if (data.strasse || data.hausnummer) {
        const address = [data.strasse, data.hausnummer].filter(Boolean).join(' ');
        html += `<p class="sender-value">${address}</p>`;
    }

    if (data.plz || data.ort) {
        const city = [data.plz, data.ort].filter(Boolean).join(' ');
        html += `<p class="sender-value">${city}</p>`;
    }

    // Kontaktdaten
    if (data.telefon) {
        html += `
            <p class="mt-3">
                <span class="sender-label"><i class="bi bi-telephone"></i> Telefon:</span>
                <span class="sender-value">${data.telefon}</span>
            </p>
        `;
    }

    if (data.email) {
        html += `
            <p>
                <span class="sender-label"><i class="bi bi-envelope"></i> E-Mail:</span>
                <span class="sender-value">${data.email}</span>
            </p>
        `;
    }

    // Bankdaten (optional anzeigen, wenn vorhanden)
    if (data.kontoinhaber || data.iban || data.bic || data.kreditinstitut) {
        html += '<hr class="my-3" style="border-color: #374151;">';
        html += '<p class="text-muted mb-2"><small><i class="bi bi-bank"></i> Bankdaten</small></p>';

        if (data.kontoinhaber) {
            html += `<p><span class="sender-label">Kontoinhaber:</span> <span class="sender-value">${data.kontoinhaber}</span></p>`;
        }
        if (data.iban) {
            html += `<p><span class="sender-label">IBAN:</span> <span class="sender-value">${data.iban}</span></p>`;
        }
        if (data.bic || data.kreditinstitut) {
            const bank = [data.kreditinstitut, data.bic ? `(${data.bic})` : ''].filter(Boolean).join(' ');
            html += `<p><span class="sender-label">Bank:</span> <span class="sender-value">${bank}</span></p>`;
        }
    }

    html += '</div>';
    senderDataDisplay.innerHTML = html;
}

/**
 * Event Handler für das Formular-Submit
 */
async function handleFormSubmit(e) {
    e.preventDefault();

    try {
        // Speichere alle Ärzte
        await saveDoctors();

        // Aktualisiere die Anzeige
        await displaySenderData();

        // Schließe das Modal
        closeSenderModalHandler();

        console.log('Absender-Daten gespeichert');
    } catch (error) {
        // Fehlerbehandlung bereits in saveDoctors
        console.error('Fehler beim Speichern der Absender-Daten:', error);
    }
}

// Event Listeners
editSenderBtn.addEventListener('click', openSenderModal);
closeSenderModal.addEventListener('click', closeSenderModalHandler);
cancelSenderBtn.addEventListener('click', closeSenderModalHandler);
senderDataForm.addEventListener('submit', handleFormSubmit);
setActiveDoctorBtn.addEventListener('click', setActiveDoctorHandler);

// Navigation-Event-Listeners
prevDoctorBtn.addEventListener('click', () => {
    switchDoctor(currentDoctorIndex - 1);
});

nextDoctorBtn.addEventListener('click', () => {
    switchDoctor(currentDoctorIndex + 1);
});

// Schließe Modal bei Klick auf Overlay (außerhalb des Modals)
senderModal.addEventListener('click', (e) => {
    if (e.target === senderModal) {
        closeSenderModalHandler();
    }
});

// ESC-Taste zum Schließen des Modals
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !senderModal.classList.contains('d-none')) {
        closeSenderModalHandler();
    }
});

/**
 * Synchronisiert die Höhe der beiden Spalten (Formularauswahl und Absender-Daten)
 * Die rechte Spalte (Absender-Daten) wird auf die Höhe der linken Spalte (Formularauswahl) begrenzt
 */
function syncContainerHeights() {
    const twoColumnLayout = document.querySelector('.two-column-layout');
    if (!twoColumnLayout) return;

    const leftCard = twoColumnLayout.querySelector('div:first-child .card');
    const rightCard = twoColumnLayout.querySelector('div:nth-child(2) .card');

    if (leftCard && rightCard) {
        // Hole die tatsächliche Höhe der linken Card
        const leftHeight = leftCard.offsetHeight;

        // Setze die maximale Höhe der rechten Card auf die Höhe der linken Card
        rightCard.style.maxHeight = `${leftHeight}px`;

        console.log(`Container-Höhen synchronisiert: ${leftHeight}px`);
    }
}

// Beim Laden der Seite die gespeicherten Daten anzeigen
document.addEventListener('DOMContentLoaded', () => {
    displaySenderData().then(() => {
        // Nach dem Laden der Daten die Höhen synchronisieren
        // Verzögerung, um sicherzustellen, dass das DOM vollständig gerendert ist
        setTimeout(syncContainerHeights, 100);
    });
});

// Bei Fenstergrößenänderung die Höhen neu synchronisieren
window.addEventListener('resize', () => {
    syncContainerHeights();
});

/**
 * Exportiere Funktion zum Abrufen der Absender-Daten für andere Module
 * (z.B. für das Ausfüllen von Formularen)
 * Gibt ein Promise zurück, das den aktiven Arzt enthält
 */
window.getSenderDataForForms = getSenderData;
