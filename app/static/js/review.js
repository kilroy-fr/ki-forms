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
});
