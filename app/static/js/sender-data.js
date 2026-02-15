/**
 * Absender-Daten Verwaltung
 * Verwaltet die Eingabe, Speicherung und Anzeige der Absender-Daten
 */

// DOM Elemente
const editSenderBtn = document.getElementById('editSenderBtn');
const senderModal = document.getElementById('senderModal');
const closeSenderModal = document.getElementById('closeSenderModal');
const cancelSenderBtn = document.getElementById('cancelSenderBtn');
const senderDataForm = document.getElementById('senderDataForm');
const senderDataDisplay = document.getElementById('senderDataDisplay');

/**
 * Öffnet das Modal zur Bearbeitung der Absender-Daten
 */
async function openSenderModal() {
    // Lade vorhandene Daten und fülle das Formular
    const savedData = await getSenderData();
    if (savedData) {
        fillForm(savedData);
    }
    senderModal.classList.remove('d-none');
}

/**
 * Schließt das Modal
 */
function closeSenderModalHandler() {
    senderModal.classList.add('d-none');
    senderDataForm.reset();
}

/**
 * Füllt das Formular mit gespeicherten Daten
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
 * Speichert die Absender-Daten im Backend
 */
async function saveSenderData(data) {
    try {
        const response = await fetch('/api/sender-data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data),
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
 * Lädt die Absender-Daten vom Backend
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
        return Object.keys(data).length > 0 ? data : null;
    } catch (error) {
        console.error('Fehler beim Laden:', error);
        return null;
    }
}

/**
 * Zeigt die gespeicherten Absender-Daten an
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

    // Erstelle HTML für die Anzeige
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

    // Sammle alle Formulardaten
    const formData = new FormData(senderDataForm);
    const data = {};

    formData.forEach((value, key) => {
        data[key] = value.trim();
    });

    try {
        // Speichere die Daten
        await saveSenderData(data);

        // Aktualisiere die Anzeige
        await displaySenderData();

        // Schließe das Modal
        closeSenderModalHandler();

        // Zeige Erfolgsbenachrichtigung (optional)
        console.log('Absender-Daten gespeichert:', data);
    } catch (error) {
        // Fehlerbehandlung bereits in saveSenderData
        console.error('Fehler beim Speichern der Absender-Daten:', error);
    }
}

// Event Listeners
editSenderBtn.addEventListener('click', openSenderModal);
closeSenderModal.addEventListener('click', closeSenderModalHandler);
cancelSenderBtn.addEventListener('click', closeSenderModalHandler);
senderDataForm.addEventListener('submit', handleFormSubmit);

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
 * Gibt ein Promise zurück, das die Absender-Daten enthält
 */
window.getSenderDataForForms = getSenderData;
