document.addEventListener("DOMContentLoaded", () => {

    document.querySelectorAll(".order-card").forEach((card, index) => {
        card.style.animationDelay = `${index * 70}ms`;
    });

});