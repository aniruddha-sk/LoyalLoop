document.addEventListener("DOMContentLoaded", () => {

    const progress = document.querySelector(".progress-fill");

    if(progress){

        let value = Number(progress.dataset.progress || 0);

        value = Math.max(0, Math.min(100, value));

        setTimeout(() => {
            progress.style.width = `${value}%`;
        }, 180);
    }

    document.querySelectorAll(".history-item").forEach((item,index) => {
        item.style.opacity = "0";
        item.style.transform = "translateY(10px)";

        setTimeout(() => {
            item.style.transition = ".35s ease";
            item.style.opacity = "1";
            item.style.transform = "translateY(0)";
        }, 100 + index * 70);
    });

});