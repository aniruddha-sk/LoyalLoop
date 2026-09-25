document.addEventListener("DOMContentLoaded", () => {

    createConfetti();

    if (navigator.vibrate) {
        navigator.vibrate([40, 30, 70]);
    }

});

function createConfetti(){

    const container = document.getElementById("confettiLayer");

    if (!container) return;

    const pieces = 45;

    for(let i = 0; i < pieces; i++){

        const piece = document.createElement("span");

        piece.className = "confetti";

        piece.style.left = Math.random() * 100 + "%";
        piece.style.animationDuration =
            (2.5 + Math.random() * 2.5) + "s";

        piece.style.animationDelay =
            Math.random() * 1.5 + "s";

        piece.style.transform =
            `rotate(${Math.random() * 360}deg)`;

        const size = 5 + Math.random() * 7;

        piece.style.width = size + "px";
        piece.style.height = (size * 1.5) + "px";

        const colors = [
            "#8b5cf6",
            "#ec4899",
            "#fbbf24",
            "#22c55e",
            "#38bdf8",
            "#f97316"
        ];

        piece.style.background =
            colors[Math.floor(Math.random() * colors.length)];

        container.appendChild(piece);

        setTimeout(() => {
            piece.remove();
        }, 6500);
    }
}

async function copyClaimCode(){

    const codeElement = document.getElementById("claimCode");
    const copyText = document.getElementById("copyText");
    const copyIcon = document.getElementById("copyIcon");

    if (!codeElement) return;

    const code = codeElement.innerText.trim();

    try{

        await navigator.clipboard.writeText(code);

        copyText.innerText = "Copied!";
        copyIcon.innerText = "✓";

        if (navigator.vibrate) {
            navigator.vibrate(30);
        }

        setTimeout(() => {
            copyText.innerText = "Copy";
            copyIcon.innerText = "⧉";
        }, 1800);

    }catch(error){

        const textarea = document.createElement("textarea");

        textarea.value = code;
        document.body.appendChild(textarea);

        textarea.select();

        document.execCommand("copy");

        textarea.remove();

        copyText.innerText = "Copied!";
        copyIcon.innerText = "✓";

        setTimeout(() => {
            copyText.innerText = "Copy";
            copyIcon.innerText = "⧉";
        }, 1800);
    }
}