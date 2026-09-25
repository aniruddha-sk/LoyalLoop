document.addEventListener("DOMContentLoaded", () => {

    document.querySelectorAll(".locked-fill").forEach((bar, index) => {
        const progress = Math.max(
            0,
            Math.min(100, Number(bar.dataset.progress || 0))
        );

        setTimeout(() => {
            bar.style.width = `${progress}%`;
        }, 150 + index * 100);
    });

    document.querySelectorAll(".reward-card").forEach((card, index) => {
        card.style.animationDelay = `${index * 70}ms`;
    });
});

async function claimReward(rewardId, button){

    if(!rewardId || button.disabled){
        return;
    }

    button.disabled = true;
    button.dataset.originalText = button.innerHTML;
    button.innerHTML = "Claiming...";

    try{

        const response = await fetch(
            window.CUSTOMER_REWARD_CLAIM_URL,
            {
                method:"POST",
                headers:{
                    "Content-Type":"application/json"
                },
                body:JSON.stringify({
                    reward_id:rewardId
                })
            }
        );

        const result = await response.json();

        if(!response.ok || !result.success){
            throw new Error(
                result.message || "Unable to claim reward."
            );
        }

        showRewardBoom(
            result.reward_name,
            result.claim_code
        );

    }catch(error){

        alert(error.message);

        button.disabled = false;
        button.innerHTML = button.dataset.originalText;
    }
}

function showRewardBoom(rewardName, claimCode){

    const overlay = document.createElement("div");
    overlay.className = "reward-boom";

    const stars = [
        ["⭐","12%","18%"],
        ["✨","82%","20%"],
        ["🎉","15%","78%"],
        ["⭐","85%","75%"],
        ["✨","50%","8%"],
        ["🎊","7%","50%"]
    ];

    const starHTML = stars.map(star => `
        <i
            style="
                left:${star[1]};
                top:${star[2]};
                --x:${Math.random() * 220 - 110}px;
                --y:${Math.random() * 220 - 110}px;
            ">
            ${star[0]}
        </i>
    `).join("");

    overlay.innerHTML = `
        <div class="boom-box">

            <div class="boom-stars">
                ${starHTML}
            </div>

            <div class="boom-icon">🎁</div>

            <h2>Reward Unlocked! 🎉</h2>

            <p>
                Congratulations! You successfully claimed
                <strong>${escapeHtml(rewardName)}</strong>.
            </p>

            <div class="claim-code">
                <span>YOUR CLAIM CODE</span>
                <strong>${escapeHtml(claimCode)}</strong>
            </div>

            <button onclick="closeRewardBoom()">
                Awesome! ✓
            </button>

        </div>
    `;

    document.body.appendChild(overlay);
}

function showClaimCode(code){

    const overlay = document.createElement("div");
    overlay.className = "reward-boom";

    overlay.innerHTML = `
        <div class="boom-box">

            <div class="boom-icon">🎟️</div>

            <h2>Your Reward</h2>

            <p>
                Show this claim code to the business
                when redeeming your reward.
            </p>

            <div class="claim-code">
                <span>CLAIM CODE</span>
                <strong>${escapeHtml(code)}</strong>
            </div>

            <button onclick="closeRewardBoom()">
                Close
            </button>

        </div>
    `;

    document.body.appendChild(overlay);
}

function closeRewardBoom(){

    const overlay = document.querySelector(".reward-boom");

    if(overlay){
        overlay.remove();
        window.location.reload();
    }
}

function escapeHtml(value){
    return String(value)
        .replace(/&/g,"&amp;")
        .replace(/</g,"&lt;")
        .replace(/>/g,"&gt;")
        .replace(/"/g,"&quot;")
        .replace(/'/g,"&#039;");
}