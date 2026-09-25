const cartBusinessId = window.LOYALLOOP_BUSINESS_ID || "default";
const customerCartKey = `loyalloop_cart_${cartBusinessId}`;

let customerCart = JSON.parse(
    localStorage.getItem(customerCartKey) || "[]"
);

document.addEventListener("DOMContentLoaded", () => {
    renderCart();

    document.getElementById("checkoutBtn")
        .addEventListener("click", goToCheckout);
});

function saveCustomerCart(){
    localStorage.setItem(
        customerCartKey,
        JSON.stringify(customerCart)
    );
}

function renderCart(){
    const container = document.getElementById("cartItems");
    const empty = document.getElementById("emptyCart");
    const bill = document.getElementById("billCard");
    const checkout = document.getElementById("checkoutBtn");

    if(!customerCart.length){
        container.innerHTML = "";
        empty.style.display = "block";
        bill.style.display = "none";
        checkout.style.display = "none";
        updateCount(0);
        return;
    }

    empty.style.display = "none";
    bill.style.display = "block";
    checkout.style.display = "flex";

    container.innerHTML = customerCart.map((item,index) => {

        const total = item.price * item.quantity;

        return `
            <article class="cart-item">

                <div class="item-image">
                    ${
                        item.image
                        ? `<img src="${escapeHtml(item.image)}" alt="${escapeHtml(item.name)}">`
                        : `<div class="item-placeholder">🍽️</div>`
                    }
                </div>

                <div class="item-info">

                    <h3>${escapeHtml(item.name)}</h3>

                    <div class="item-price">
                        ₹${Number(item.price).toFixed(2)}
                    </div>

                    <div class="item-controls">

                        <div class="quantity">
                            <button onclick="changeQuantity(${index},-1)">−</button>
                            <span>${item.quantity}</span>
                            <button onclick="changeQuantity(${index},1)">+</button>
                        </div>

                        <strong class="item-total">
                            ₹${total.toFixed(2)}
                        </strong>

                    </div>

                    <button
                        class="remove-btn"
                        onclick="removeItem(${index})">
                        Remove
                    </button>

                </div>

            </article>
        `;
    }).join("");

    calculateTotal();
}

function changeQuantity(index,change){
    customerCart[index].quantity += change;

    if(customerCart[index].quantity <= 0){
        customerCart.splice(index,1);
    }

    saveCustomerCart();
    renderCart();
}

function removeItem(index){
    customerCart.splice(index,1);
    saveCustomerCart();
    renderCart();
}

function calculateTotal(){
    const subtotal = customerCart.reduce(
        (sum,item) => sum + (Number(item.price) * item.quantity),
        0
    );

    document.getElementById("subtotal").textContent =
        `₹${subtotal.toFixed(2)}`;

    document.getElementById("grandTotal").textContent =
        `₹${subtotal.toFixed(2)}`;

    document.getElementById("checkoutTotal").textContent =
        `₹${subtotal.toFixed(2)}`;

    updateCount(
        customerCart.reduce(
            (sum,item) => sum + item.quantity,
            0
        )
    );
}

function updateCount(count){
    document.getElementById("totalItems").textContent =
        `${count} ${count === 1 ? "item" : "items"}`;

    const navCount = document.getElementById("navCartCount");

    navCount.textContent = count;
    navCount.style.display = count ? "flex" : "none";
}

function goToCheckout(){
    if(!customerCart.length){
        return;
    }

    window.location.href = window.CUSTOMER_ORDER_URL;
}

function escapeHtml(value){
    return String(value)
        .replace(/&/g,"&amp;")
        .replace(/</g,"&lt;")
        .replace(/>/g,"&gt;")
        .replace(/"/g,"&quot;")
        .replace(/'/g,"&#039;");
}