console.log("MCQ Admin Panel Loaded");

document.addEventListener("DOMContentLoaded", function () {
    var deleteForms = document.querySelectorAll(".delete-form");

    deleteForms.forEach(function (form) {
        form.addEventListener("submit", function (event) {
            var confirmed = window.confirm("Are you sure you want to delete this?");
            if (!confirmed) {
                event.preventDefault();
            }
        });
    });
});