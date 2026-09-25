document.addEventListener("DOMContentLoaded", () => {

    const form =
        document.getElementById("customerLoginForm");

    const phone =
        document.getElementById("phone");

    const phoneError =
        document.getElementById("phoneError");

    const loginButton =
        document.getElementById("loginButton");


    if (!form) {
        return;
    }


    /* =========================================
       PHONE INPUT
    ========================================= */

    if (phone) {

        phone.addEventListener("input", () => {

            phone.value = phone.value
                .replace(/\D/g, "")
                .slice(0, 10);

            if (phoneError) {
                phoneError.textContent = "";
            }

            phone.style.borderColor = "";

        });

    }


    /* =========================================
       FORM SUBMIT
    ========================================= */

    form.addEventListener("submit", (event) => {

        const value = phone
            ? phone.value.trim()
            : "";


        /* =====================================
           VALIDATE MOBILE
        ===================================== */

        if (!/^[6-9]\d{9}$/.test(value)) {

            event.preventDefault();

            if (phoneError) {

                phoneError.textContent =
                    "Enter a valid 10-digit mobile number.";

                phoneError.style.color =
                    "#f87171";

                phoneError.style.fontSize =
                    "10px";

                phoneError.style.marginTop =
                    "5px";

                phoneError.style.display =
                    "block";
            }


            if (phone) {

                phone.style.borderColor =
                    "#ef4444";

                phone.focus();

            }

            return;
        }


        /* =====================================
           VALID PHONE
           ===================================== */

        if (phoneError) {
            phoneError.textContent = "";
        }

        if (phone) {
            phone.style.borderColor = "";
        }


        /* =====================================
           BUTTON LOADING
           
           IMPORTANT:
           DO NOT event.preventDefault()
           
           Browser will submit POST to Flask.
        ===================================== */

        if (loginButton) {

            loginButton.disabled = true;

            const buttonText =
                loginButton.querySelector(
                    ".button-text"
                );

            if (buttonText) {

                buttonText.textContent =
                    "Checking...";

            }

        }

    });

});