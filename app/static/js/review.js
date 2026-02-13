document.addEventListener("DOMContentLoaded", function () {
    // Felder hervorheben, die vom User geaendert werden
    const inputs = document.querySelectorAll(
        'input[type="text"], textarea'
    );

    inputs.forEach(function (input) {
        const originalValue = input.value;
        input.addEventListener("input", function () {
            if (input.value !== originalValue) {
                input.classList.add("border-primary");
            } else {
                input.classList.remove("border-primary");
            }
        });
    });

    // Formular-Submit: Ladeindikator
    const form = document.querySelector("form");
    if (form) {
        form.addEventListener("submit", function () {
            const btn = form.querySelector('button[type="submit"]');
            if (btn) {
                btn.disabled = true;
                btn.innerHTML =
                    '<span class="spinner-border spinner-border-sm me-2"></span>PDF wird erstellt...';
            }
        });
    }

    // Bedingte Felder in Sektion 11
    function updateConditionalFields() {
        // Alle bedingten Felder durchgehen
        const conditionalFields = document.querySelectorAll('.conditional-field');

        conditionalFields.forEach(function(field) {
            const dependsOn = field.getAttribute('data-depends-on');
            if (dependsOn) {
                // Prüfen, ob das Radio-Button mit diesem Wert ausgewählt ist
                const trigger = document.getElementById(dependsOn);
                if (trigger && trigger.type === 'radio' && trigger.checked) {
                    field.classList.add('show');
                } else {
                    field.classList.remove('show');
                }
            }
        });
    }

    // Event-Listener für alle conditional-trigger Radio-Buttons
    const conditionalTriggers = document.querySelectorAll('.conditional-trigger');
    conditionalTriggers.forEach(function(trigger) {
        trigger.addEventListener('change', updateConditionalFields);
    });

    // Initial die bedingten Felder aktualisieren
    updateConditionalFields();
});
