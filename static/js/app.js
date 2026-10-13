(function () {
  const byId = (id) => document.getElementById(id);

  // 1. Highlight the current page in the sidebar
  const path = window.location.pathname;
  document.querySelectorAll(".sidebar .nav-link").forEach((link) => {
    const href = link.getAttribute("href");
    if (href === "/" ? path === "/" : path.startsWith(href)) link.classList.add("active");
  });

  // 2. Sale / purchase forms: auto-fill price, show stock and live total
  const dataEl = byId("products-data");
  if (!dataEl) return;

  const products = JSON.parse(dataEl.textContent);
  const product = byId("id_product");
  const qty = byId("id_quantity");
  const sellPrice = byId("id_selling_price");           // only on the sale form
  const price = sellPrice || byId("id_purchase_price"); // price field of this form
  const discount = byId("id_discount");
  const payment = byId("id_payment_method");
  const customerRow = byId("row_customer");

  function updateTotal() {
    const gross = Number(qty.value || 0) * Number(price.value || 0);
    const total = gross - Number(discount ? discount.value || 0 : 0);
    byId("total-info").textContent = "₹" + total.toFixed(2);
  }

  function showStock() {
    const p = products[product.value];
    byId("stock-info").textContent = p ? p.stock : "-";
  }

  function toggleCustomer() {
    if (payment) customerRow.classList.toggle("d-none", payment.value !== "Udhaar");
  }

  product.addEventListener("change", () => {
    const p = products[product.value];
    if (p) price.value = sellPrice ? p.sell : p.cost;
    showStock();
    updateTotal();
  });
  [qty, price, discount].forEach((el) => el && el.addEventListener("input", updateTotal));
  if (payment) payment.addEventListener("change", toggleCustomer);

  showStock();
  updateTotal();
  toggleCustomer();
})();
