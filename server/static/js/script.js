console.log("MCQ Admin Panel Loaded");

document.addEventListener("DOMContentLoaded", function () {
    var deleteForms = document.querySelectorAll(".delete-form");

    deleteForms.forEach(function (form) {
        form.addEventListener("submit", function (event) {
            var message = form.getAttribute("data-confirm") || "Are you sure you want to delete this?";
            var confirmed = window.confirm(message);
            if (!confirmed) {
                event.preventDefault();
            }
        });
    });
});