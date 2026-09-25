document.addEventListener("DOMContentLoaded", () => {

    const status = window.ORDER_STATUS;

    if (!status || status === "cancelled" || status === "delivered") {
        return;
    }

    document.querySelectorAll(".timeline-step").forEach((step, index) => {
        step.style.animationDelay = `${index * 100}ms`;
    });

});