document.addEventListener("DOMContentLoaded",()=>{

    const loader=document.getElementById("customer-loader");

    if(!loader){
        return;
    }

    const showLoader=()=>{

        loader.classList.remove("hide");
        document.body.classList.add("customer-loading");

    };

    const hideLoader=()=>{

        loader.classList.add("hide");
        document.body.classList.remove("customer-loading");

    };


    /*
       SHOW CUSTOMER LOADER
    */

    showLoader();


    /*
       HIDE EXACTLY WHEN PAGE FINISHES LOADING
    */

    if(document.readyState==="complete"){

        hideLoader();

    }else{

        window.addEventListener(
            "load",
            hideLoader,
            {once:true}
        );

    }


    /*
       CUSTOMER PAGE NAVIGATION
    */

    document.addEventListener("click",event=>{

        const link=event.target.closest("a");

        if(!link){
            return;
        }


        if(
            event.defaultPrevented||
            event.button!==0||
            event.metaKey||
            event.ctrlKey||
            event.shiftKey||
            event.altKey
        ){
            return;
        }


        const href=link.getAttribute("href");


        if(
            !href||
            href==="#"||
            href.startsWith("#")||
            href.startsWith("javascript:")||
            link.target==="_blank"||
            link.hasAttribute("download")
        ){
            return;
        }


        let url;

        try{

            url=new URL(
                href,
                window.location.href
            );

        }catch{

            return;

        }


        /*
           EXTERNAL LINK
        */

        if(url.origin!==window.location.origin){
            return;
        }


        const currentPath=window.location.pathname;

        const nextPath=url.pathname;


        /*
           CURRENT CUSTOMER PAGE
        */

        const currentCustomer=
            currentPath.startsWith("/customer")||
            currentPath.startsWith("/business/");


        /*
           NEXT CUSTOMER PAGE
        */

        const nextCustomer=
            nextPath.startsWith("/customer")||
            nextPath.startsWith("/business/");


        /*
           ONLY CUSTOMER → CUSTOMER
        */

        if(!currentCustomer||!nextCustomer){
            return;
        }


        /*
           SHOW CUSTOMER LOADER
        */

        showLoader();

    });


    /*
       BROWSER BACK / FORWARD CACHE
    */

    window.addEventListener(
        "pageshow",
        event=>{

            if(event.persisted){

                hideLoader();

            }

        }
    );

});