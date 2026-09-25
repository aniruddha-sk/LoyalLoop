const checkoutBusinessId = window.LOYALLOOP_BUSINESS_ID || "default";
const checkoutCartKey = `loyalloop_cart_${checkoutBusinessId}`;

let checkoutCart = JSON.parse(
    localStorage.getItem(checkoutCartKey) || "[]"
);

document.addEventListener("DOMContentLoaded", () => {
    renderCheckoutItems();
    updateNoteCount();

    document.getElementById("customerNote")
        .addEventListener("input", updateNoteCount);

    document.getElementById("placeOrderBtn")
        .addEventListener("click", placeOrder);
});

function renderCheckoutItems(){
    const container = document.getElementById("checkoutItems");

    if(!checkoutCart.length){
        window.location.href = "/customer/menu";
        return;
    }

    container.innerHTML = checkoutCart.map(item => {

        const total = Number(item.price) * item.quantity;

        return `
            <div class="checkout-item">

                <div class="checkout-item-image">
                    ${
                        item.image
                        ? `<img src="${escapeHtml(item.image)}"
                                alt="${escapeHtml(item.name)}">`
                        : `<div class="checkout-item-placeholder">🍽️</div>`
                    }
                </div>

                <div class="checkout-item-info">
                    <h3>${escapeHtml(item.name)}</h3>
                    <span>
                        ₹${Number(item.price).toFixed(2)}
                        × ${item.quantity}
                    </span>
                </div>

                <strong class="checkout-item-total">
                    ₹${total.toFixed(2)}
                </strong>

            </div>
        `;
    }).join("");

    updateTotals();
}

function updateTotals(){
    const subtotal = checkoutCart.reduce(
        (sum,item) => sum + Number(item.price) * item.quantity,
        0
    );

    document.getElementById("checkoutSubtotal").textContent =
        `₹${subtotal.toFixed(2)}`;

    document.getElementById("checkoutGrandTotal").textContent =
        `₹${subtotal.toFixed(2)}`;

    document.getElementById("placeOrderTotal").textContent =
        `₹${subtotal.toFixed(2)}`;
}

function updateNoteCount(){
    const note = document.getElementById("customerNote");

    document.getElementById("noteCount").textContent =
        note.value.length;
}

async function placeOrder(){

    if(!checkoutCart.length){
        return;
    }

    const button = document.getElementById("placeOrderBtn");
    const note = document.getElementById("customerNote").value.trim();

    button.disabled = true;
    button.querySelector("span").textContent = "Placing Order...";

    const payload = {
        items: checkoutCart.map(item => ({
            menu_item_id: item.id,
            quantity: item.quantity
        })),
        customer_note: note
    };

    try{

        const response = await fetch(
            window.CUSTOMER_ORDER_SUBMIT_URL,
            {
                method:"POST",
                headers:{
                    "Content-Type":"application/json"
                },
                body:JSON.stringify(payload)
            }
        );

        const result = await response.json();

        if(!response.ok || !result.success){
            throw new Error(
                result.message || "Unable to place order."
            );
        }

        localStorage.removeItem(checkoutCartKey);

        showSuccess(result.order_number);

    }catch(error){

        alert(error.message);

        button.disabled = false;
        button.querySelector("span").textContent = "Place Order";
    }
}

function showSuccess(orderNumber){

    const overlay = document.createElement("div");

    overlay.className = "order-success";

    overlay.innerHTML = `
        <div class="success-box">

            <div class="success-icon">✓</div>

            <h2>Order Placed!</h2>

            <p>
                Your order has been successfully placed.
                <br>
                Order #${escapeHtml(orderNumber)}
            </p>

            <a href="/customer/orders">
                View My Orders →
            </a>

        </div>
    `;

    document.body.appendChild(overlay);
}

function escapeHtml(value){
    return String(value)
        .replace(/&/g,"&amp;")
        .replace(/</g,"&lt;")
        .replace(/>/g,"&gt;")
        .replace(/"/g,"&quot;")
        .replace(/'/g,"&#039;");
}