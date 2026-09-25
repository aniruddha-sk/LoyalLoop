/* =========================================
   LOYALLOOP CUSTOMER BASE JS
   ========================================= */

document.addEventListener("DOMContentLoaded", () => {

    const app = document.getElementById("customerApp");
    const toastContainer = document.getElementById("customerToastContainer");

    const modalLayer = document.getElementById("customerModalLayer");
    const modal = document.getElementById("customerModal");
    const modalContent = document.getElementById("customerModalContent");
    const modalClose = document.getElementById("customerModalClose");
    const modalBackdrop = document.getElementById("customerModalBackdrop");

    const celebration = document.getElementById("customerCelebration");
    const celebrationIcon = document.getElementById("celebrationIcon");
    const celebrationTitle = document.getElementById("celebrationTitle");
    const celebrationMessage = document.getElementById("celebrationMessage");
    const celebrationClose = document.getElementById("celebrationClose");

    const cartBadge = document.getElementById("customerCartBadge");


    /* =========================================
       NAVIGATION TOUCH EFFECT
       ========================================= */

    document.querySelectorAll(".customer-nav-item").forEach(item => {

        item.addEventListener("click", () => {

            item.classList.remove("nav-pulse");

            void item.offsetWidth;

            item.classList.add("nav-pulse");

        });

    });


    /* =========================================
       CART BADGE
       ========================================= */

    window.updateCustomerCartBadge = function(count) {

        if (!cartBadge) {
            return;
        }

        const total = Number(count) || 0;

        cartBadge.textContent = total > 99 ? "99+" : total;

        if (total > 0) {

            cartBadge.classList.add("show");

        } else {

            cartBadge.classList.remove("show");

        }

    };


    /* =========================================
       TOAST
       ========================================= */

    window.showCustomerToast = function(
        title,
        message = "",
        icon = "✓"
    ) {

        if (!toastContainer) {
            return;
        }

        const toast = document.createElement("div");

        toast.className = "customer-toast";

        toast.innerHTML = `
            <div class="customer-toast-icon">
                ${icon}
            </div>

            <div>
                <strong>${escapeCustomerHTML(title)}</strong>
                ${
                    message
                    ? `<span>${escapeCustomerHTML(message)}</span>`
                    : ""
                }
            </div>
        `;

        toastContainer.appendChild(toast);

        setTimeout(() => {

            toast.classList.add("removing");

            setTimeout(() => {

                toast.remove();

            }, 350);

        }, 3000);

    };


    /* =========================================
       MODAL
       ========================================= */

    window.openCustomerModal = function(content) {

        if (!modalLayer || !modalContent) {
            return;
        }

        modalContent.innerHTML = content;

        modalLayer.classList.add("show");

        document.body.classList.add("no-scroll");

    };


    window.closeCustomerModal = function() {

        if (!modalLayer) {
            return;
        }

        modalLayer.classList.remove("show");

        document.body.classList.remove("no-scroll");

    };


    if (modalClose) {

        modalClose.addEventListener(
            "click",
            window.closeCustomerModal
        );

    }


    if (modalBackdrop) {

        modalBackdrop.addEventListener(
            "click",
            window.closeCustomerModal
        );

    }


    document.addEventListener("keydown", event => {

        if (event.key === "Escape") {

            window.closeCustomerModal();

            window.closeCustomerCelebration();

        }

    });


    /* =========================================
       CELEBRATION
       ========================================= */

    window.showCustomerCelebration = function(
        title = "Amazing!",
        message = "You just unlocked something special.",
        icon = "🎉"
    ) {

        if (!celebration) {
            return;
        }

        celebrationIcon.textContent = icon;
        celebrationTitle.textContent = title;
        celebrationMessage.textContent = message;

        celebration.classList.add("show");

        document.body.classList.add("no-scroll");

        createCelebrationParticles();

    };


    window.closeCustomerCelebration = function() {

        if (!celebration) {
            return;
        }

        celebration.classList.remove("show");

        document.body.classList.remove("no-scroll");

    };


    if (celebrationClose) {

        celebrationClose.addEventListener(
            "click",
            window.closeCustomerCelebration
        );

    }


    /* =========================================
       PARTICLES
       ========================================= */

    function createCelebrationParticles() {

        const container = document.querySelector(
            ".customer-celebration"
        );

        if (!container) {
            return;
        }

        container
            .querySelectorAll(".celebration-particle")
            .forEach(particle => particle.remove());

        const symbols = [
            "✦",
            "✧",
            "•",
            "✦",
            "★",
            "◇",
            "✧",
            "•"
        ];

        for (let i = 0; i < 24; i++) {

            const particle = document.createElement("span");

            particle.className =
                "celebration-particle";

            particle.textContent =
                symbols[
                    Math.floor(
                        Math.random() * symbols.length
                    )
                ];

            particle.style.left =
                `${Math.random() * 100}%`;

            particle.style.top =
                `${30 + Math.random() * 50}%`;

            particle.style.animationDelay =
                `${Math.random() * .6}s`;

            particle.style.setProperty(
                "--particle-x",
                `${(Math.random() - .5) * 260}px`
            );

            particle.style.setProperty(
                "--particle-y",
                `${-80 - Math.random() * 220}px`
            );

            container.appendChild(particle);

        }

    }


    /* =========================================
       HTML ESCAPE
       ========================================= */

    function escapeCustomerHTML(value) {

        return String(value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");

    }


    /* =========================================
       PAGE ENTER
       ========================================= */

    if (app) {

        requestAnimationFrame(() => {

            app.classList.add("customer-ready");

        });

    }

});