const businessId = window.LOYALLOOP_BUSINESS_ID || "default";
const cartKey = `loyalloop_cart_${businessId}`;

let cart = JSON.parse(localStorage.getItem(cartKey) || "[]");

document.addEventListener("DOMContentLoaded", () => {
    updateCartCount();
    setupSearch();
    setupCategories();
});

function saveCart() {
    localStorage.setItem(cartKey, JSON.stringify(cart));
    updateCartCount();
}

function addToCart(button) {
    const card = button.closest(".food-card");

    const id = card.dataset.id;
    const name = card.dataset.itemName;
    const price = Number(card.dataset.price);
    const image = card.dataset.image || "";

    const existing = cart.find(item => item.id === id);

    if (existing) {
        existing.quantity += 1;
    } else {
        cart.push({
            id,
            name,
            price,
            image,
            quantity: 1
        });
    }

    saveCart();

    button.innerHTML = "✓ Added";
    button.classList.add("added");

    showCartMessage(`${name} added to cart`);

    setTimeout(() => {
        button.innerHTML = "<span>+</span> Add";
        button.classList.remove("added");
    }, 900);
}

function updateCartCount() {
    const count = cart.reduce((total, item) => total + item.quantity, 0);

    const cartCount = document.getElementById("cartCount");
    const navCartCount = document.getElementById("navCartCount");

    if (cartCount) {
        cartCount.textContent = count;
        cartCount.style.display = count ? "flex" : "none";
    }

    if (navCartCount) {
        navCartCount.textContent = count;
        navCartCount.style.display = count ? "flex" : "none";
    }
}

function setupSearch() {
    const search = document.getElementById("menuSearch");

    search.addEventListener("input", () => {
        filterItems();
    });
}

function setupCategories() {
    document.querySelectorAll(".category-chip").forEach(button => {
        button.addEventListener("click", () => {

            document.querySelectorAll(".category-chip")
                .forEach(btn => btn.classList.remove("active"));

            button.classList.add("active");

            filterItems();
        });
    });
}

function filterItems() {
    const searchValue = document
        .getElementById("menuSearch")
        .value
        .trim()
        .toLowerCase();

    const activeCategory =
        document.querySelector(".category-chip.active")?.dataset.category || "all";

    let visible = 0;

    document.querySelectorAll(".food-card").forEach(card => {

        const category = card.dataset.category;
        const name = card.dataset.name;

        const categoryMatch =
            activeCategory === "all" ||
            category === activeCategory;

        const searchMatch =
            !searchValue ||
            name.includes(searchValue);

        if (categoryMatch && searchMatch) {
            card.style.display = "";
            visible++;
        } else {
            card.style.display = "none";
        }
    });

    document.getElementById("itemCount").textContent =
        `${visible} ${visible === 1 ? "item" : "items"}`;

    document.getElementById("emptyMenu").style.display =
        visible === 0 ? "block" : "none";
}

function showCartMessage(message) {
    let popup = document.querySelector(".cart-pop");

    if (!popup) {
        popup = document.createElement("div");
        popup.className = "cart-pop";
        document.body.appendChild(popup);
    }

    popup.textContent = `🛒 ${message}`;
    popup.classList.add("show");

    clearTimeout(window.cartPopupTimer);

    window.cartPopupTimer = setTimeout(() => {
        popup.classList.remove("show");
    }, 1100);
}