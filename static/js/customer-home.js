document.addEventListener("DOMContentLoaded",()=>{

    const progress=document.querySelector(".progress-fill");

    if(progress){

        const value=Math.min(
            100,
            Math.max(
                0,
                Number(progress.dataset.progress)||0
            )
        );

        setTimeout(()=>{
            progress.style.width=value+"%";
        },250);
    }

    document.querySelectorAll(".quick-card,.order-card").forEach(card=>{

        card.addEventListener("click",()=>{

            card.style.transform="scale(.98)";

            setTimeout(()=>{
                card.style.transform="";
            },130);

        });

    });

});