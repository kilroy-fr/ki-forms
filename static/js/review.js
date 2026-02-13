// Ollama-Modell beim Laden der Seite aufwärmen
document.addEventListener('DOMContentLoaded', function() {
    // Warmup-Request im Hintergrund starten
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
});
