document.addEventListener("DOMContentLoaded", () => {

    document.querySelectorAll(".quick-actions a").forEach((item,index) => {

        item.style.opacity = "0";
        item.style.transform = "translateY(10px)";

        setTimeout(() => {
            item.style.transition = ".35s ease";
            item.style.opacity = "1";
            item.style.transform = "translateY(0)";
        }, 100 + index * 80);

    });

});