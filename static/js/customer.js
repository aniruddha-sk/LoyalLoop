document.addEventListener("DOMContentLoaded",()=>{

const search=document.querySelector(".customer-search input");

if(search){
search.addEventListener("keydown",e=>{
if(e.key==="Escape"){
search.value="";
search.focus();
}
});
}

document.querySelectorAll(".customer-name,.mini-btn").forEach(link=>{
link.addEventListener("click",()=>{
link.style.opacity=".65";
});
});

});