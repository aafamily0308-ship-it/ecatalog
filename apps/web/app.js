async function fetchProducts() {
  const res = await fetch('/api/products');
  return res.json();
}

async function fetchComparison(productId) {
  const res = await fetch(`/api/compare/${productId}`);
  if (!res.ok) return null;
  return res.json();
}

function renderProducts(products) {
  const target = document.getElementById('products');
  target.innerHTML = '';

  products.forEach(async (product) => {
    const cmp = await fetchComparison(product.id);
    const li = document.createElement('li');
    const price = cmp?.best_price_azn ? `${cmp.best_price_azn} AZN` : 'no offers yet';
    li.textContent = `#${product.id} ${product.title} (${product.condition}) — best price: ${price}`;
    target.appendChild(li);
  });
}

async function refreshProducts() {
  const products = await fetchProducts();
  renderProducts(products);
}

document.getElementById('product-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = event.target;
  const payload = {
    title: form.title.value,
    brand: form.brand.value || null,
    category: form.category.value || null,
    condition: form.condition.value,
  };

  const res = await fetch('/api/products', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (res.ok) {
    form.reset();
    await refreshProducts();
  }
});

document.getElementById('offer-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = event.target;
  const payload = {
    product_id: Number(form.product_id.value),
    seller: {
      name: form.seller_name.value,
      city: form.seller_city.value || null,
    },
    price_azn: Number(form.price_azn.value),
    url: form.url.value || null,
    currency: 'AZN',
    is_available: true,
  };

  const res = await fetch('/api/offers', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (res.ok) {
    form.reset();
    await refreshProducts();
  }
});

document.getElementById('refresh').addEventListener('click', refreshProducts);
refreshProducts();
