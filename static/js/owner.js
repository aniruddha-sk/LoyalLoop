document.addEventListener("DOMContentLoaded",()=>{

const sidebar=document.getElementById("ownerSidebar");
const overlay=document.getElementById("ownerOverlay");
const menuBtn=document.getElementById("menuBtn");

if(menuBtn){
menuBtn.addEventListener("click",()=>{
sidebar.classList.toggle("open");
overlay.classList.toggle("show");
});
}

if(overlay){
overlay.addEventListener("click",()=>{
sidebar.classList.remove("open");
overlay.classList.remove("show");
});
}

document.querySelectorAll(".quick-action").forEach(item=>{
item.addEventListener("click",()=>{
item.style.transform="scale(.98)";
setTimeout(()=>item.style.transform="",150);
});
});

});