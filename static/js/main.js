/* =========================================================
   LOYALLOOP GLOBAL JAVASCRIPT
========================================================= */


/* ---------------------------------------------------------
   OWNER LOADER
--------------------------------------------------------- */

const hideLoyalLoopLoader=()=>{

    const loader=document.getElementById(
        "loyalloop-loader"
    );

    if(!loader){
        return;
    }

    requestAnimationFrame(()=>{

        loader.classList.add("hide");

    });

};


if(document.readyState==="loading"){

    document.addEventListener(
        "DOMContentLoaded",
        hideLoyalLoopLoader
    );

}else{

    hideLoyalLoopLoader();

}


/* ---------------------------------------------------------
   SHOW OWNER LOADER BEFORE OWNER PAGE NAVIGATION
--------------------------------------------------------- */

document.addEventListener("click",(event)=>{

    const link=event.target.closest("a");

    if(!link){
        return;
    }


    if(link.target==="_blank"){
        return;
    }


    if(link.hasAttribute("download")){
        return;
    }


    if(link.href.startsWith("javascript:")){
        return;
    }


    if(link.origin!==window.location.origin){
        return;
    }


    if(link.href===window.location.href){
        return;
    }


    const currentPath=window.location.pathname;

    const nextPath=new URL(
        link.href,
        window.location.href
    ).pathname;


    /*
       CURRENT PAGE IS OWNER
    */

    const currentOwner=
        currentPath.startsWith("/owner")||
        currentPath==="/analytics";


    /*
       NEXT PAGE IS OWNER
    */

    const nextOwner=
        nextPath.startsWith("/owner")||
        nextPath==="/analytics";


    /*
       ONLY OWNER → OWNER
    */

    if(!currentOwner||!nextOwner){
        return;
    }


    /*
       SHOW OWNER LOADER
    */

    const loader=document.getElementById(
        "loyalloop-loader"
    );

    if(loader){

        loader.classList.remove("hide");

    }

});


/* ---------------------------------------------------------
   AUTO REMOVE FLASH MESSAGES
--------------------------------------------------------- */

document.addEventListener(
    "DOMContentLoaded",
    ()=>{

        const messages=document.querySelectorAll(
            ".flash-message"
        );


        messages.forEach((message)=>{

            setTimeout(()=>{

                message.style.opacity="0";

                message.style.transform=
                    "translateY(-10px)";


                setTimeout(()=>{

                    message.remove();

                },300);

            },4000);

        });

    }
);