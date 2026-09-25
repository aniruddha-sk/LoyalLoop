document.addEventListener("DOMContentLoaded", () => {

    const reviewButton = document.getElementById("googleReviewBtn");

    if (!reviewButton) return;

    reviewButton.addEventListener("click", () => {

        reviewButton.classList.add("review-clicked");

        if (navigator.vibrate) {
            navigator.vibrate(35);
        }

        setTimeout(() => {
            reviewButton.classList.remove("review-clicked");
        }, 500);

    });

});