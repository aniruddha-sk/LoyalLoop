document.addEventListener("DOMContentLoaded", () => {
    const page = document.querySelector(".customer-business-page");
    if (!page) return;

    const primaryButton = document.querySelector(".business-primary-btn");

    if (primaryButton) {
        primaryButton.addEventListener("click", () => {
            primaryButton.classList.add("clicked");

            setTimeout(() => {
                primaryButton.classList.remove("clicked");
            }, 500);
        });
    }

    const cards = document.querySelectorAll(".social-card, .feature-card");

    cards.forEach((card, index) => {
        card.style.animationDelay = `${index * 80}ms`;
    });

    document.querySelectorAll('a[href^="http"], a[href^="tel:"]').forEach(link => {
        link.addEventListener("click", () => {
            link.style.transform = "scale(.97)";

            setTimeout(() => {
                link.style.transform = "";
            }, 180);
        });
    });
});