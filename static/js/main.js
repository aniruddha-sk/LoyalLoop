/* =========================================================
   LOYALLOOP GLOBAL JAVASCRIPT
========================================================= */


/* ---------------------------------------------------------
   AUTO REMOVE FLASH MESSAGES
--------------------------------------------------------- */

document.addEventListener("DOMContentLoaded", () => {

    const messages =
        document.querySelectorAll(".flash-message");

    messages.forEach((message) => {

        setTimeout(() => {

            message.style.opacity = "0";

            message.style.transform =
                "translateY(-10px)";

            setTimeout(() => {

                message.remove();

            }, 300);

        }, 4000);

    });

});