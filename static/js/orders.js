/* ============================================================
   LOYALLOOP - ORDERS JS
   ============================================================ */

document.addEventListener("DOMContentLoaded",()=>{

    document.querySelectorAll(".status-action[data-confirm]").forEach(button=>{
        button.addEventListener("click",event=>{
            const message=button.dataset.confirm;
            if(message&&!window.confirm(message)){
                event.preventDefault();
                return;
            }
            button.disabled=true;
            button.classList.add("loading");
        });
    });

    const searchInput=document.querySelector(".order-search-form input[name='search']");

    if(searchInput){
        searchInput.addEventListener("keydown",event=>{
            if(event.key==="Escape"){
                searchInput.value="";
                searchInput.focus();
            }
        });
    }

    document.querySelectorAll(".order-number").forEach(link=>{
        link.addEventListener("click",()=>{
            sessionStorage.setItem("loyalloop_last_order",link.textContent.trim());
        });
    });

});