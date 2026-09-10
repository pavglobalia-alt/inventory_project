const API_BASE = '/api/v1';

let authToken = localStorage.getItem('token') || '';
let currentUser = JSON.parse(localStorage.getItem('user') || 'null');
let userPermissions = JSON.parse(localStorage.getItem('permissions') || '[]');

let currentTab = 'dashboard';
let posCart = [];
let allProducts = [];
let allCustomers = [];
let allSuppliers = [];

// ---------------------------------------------------------
// INITIALIZATION & AUTH
// ---------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
    if (authToken && currentUser) {
        showApp();
    } else {
        showLoginModal();
    }

    document.getElementById('login-form').addEventListener('submit', handleLogin);
    document.getElementById('form-create-product').addEventListener('submit', handleCreateProduct);
    document.getElementById('form-stock-adj').addEventListener('submit', handleStockAdjustment);
    document.getElementById('form-payment').addEventListener('submit', handlePayment);
    document.getElementById('form-customer').addEventListener('submit', handleCreateCustomer);
    document.getElementById('form-supplier').addEventListener('submit', handleCreateSupplier);
});

function quickFill(email, password) {
    document.getElementById('login-email').value = email;
    document.getElementById('login-password').value = password;
}

async function handleLogin(e) {
    e.preventDefault();
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;
    const errDiv = document.getElementById('login-error');
    errDiv.innerText = '';

    try {
        const res = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        const data = await res.json();
        if (!res.ok) {
            errDiv.innerText = data.detail || 'Login failed';
            return;
        }

        authToken = data.access_token;
        currentUser = data.user;
        userPermissions = data.permissions || [];

        localStorage.setItem('token', authToken);
        localStorage.setItem('user', JSON.stringify(currentUser));
        localStorage.setItem('permissions', JSON.stringify(userPermissions));

        showApp();
    } catch (err) {
        errDiv.innerText = 'Connection error. Make sure server is running.';
    }
}

function logout() {
    authToken = '';
    currentUser = null;
    userPermissions = [];
    localStorage.clear();
    location.reload();
}

function showLoginModal() {
    document.getElementById('login-modal').classList.add('active');
    document.getElementById('app-wrapper').classList.add('hidden');
}

function showApp() {
    document.getElementById('login-modal').classList.remove('active');
    document.getElementById('app-wrapper').classList.remove('hidden');

    document.getElementById('user-display-name').innerText = currentUser.name;
    document.getElementById('user-display-email').innerText = currentUser.email;
    document.getElementById('user-role-badge').innerText = currentUser.role_name;

    applyRBACNavRestrictions();
    switchTab('dashboard');
}

// ---------------------------------------------------------
// RBAC UI PERMISSION ENFORCEMENT
// ---------------------------------------------------------
function hasPermission(module, action) {
    if (!currentUser) return false;
    if (currentUser.role_name === 'Super Admin') return true;

    const reqKeyFull = `${module}:FULL`;
    const reqKeyAction = `${module}:${action}`;
    return userPermissions.includes(reqKeyFull) || userPermissions.includes(reqKeyAction);
}

function applyRBACNavRestrictions() {
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        const module = item.getAttribute('data-module');
        if (module && !hasPermission(module, 'VIEW')) {
            item.classList.add('disabled');
        } else {
            item.classList.remove('disabled');
        }
    });
}

// ---------------------------------------------------------
// TAB NAVIGATION & ROUTING
// ---------------------------------------------------------
function switchTab(tabId) {
    const moduleMap = {
        'dashboard': 'Dashboard',
        'products': 'Products',
        'inventory': 'Inventory',
        'sales': 'Sales',
        'purchases': 'Purchases',
        'customers': 'Customers',
        'suppliers': 'Suppliers',
        'payments': 'Payments',
        'reports': 'Reports',
        'users': 'Users'
    };

    const targetModule = moduleMap[tabId];
    const banner = document.getElementById('access-restricted-banner');

    if (targetModule && !hasPermission(targetModule, 'VIEW')) {
        banner.classList.remove('hidden');
    } else {
        banner.classList.add('hidden');
    }

    currentTab = tabId;

    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab-pane').forEach(el => el.classList.remove('active'));

    const navMatch = document.querySelector(`.nav-item[onclick="switchTab('${tabId}')"]`);
    if (navMatch) navMatch.classList.add('active');

    const paneMatch = document.getElementById(`tab-${tabId}`);
    if (paneMatch) paneMatch.classList.add('active');

    document.getElementById('page-title').innerText = targetModule ? `${targetModule} Module` : 'Overview';

    loadCurrentTab();
}

function loadCurrentTab() {
    switch (currentTab) {
        case 'dashboard': loadDashboard(); break;
        case 'products': loadProducts(); break;
        case 'inventory': loadInventory(); break;
        case 'sales': loadSalesPOS(); break;
        case 'purchases': loadPurchases(); break;
        case 'customers': loadCustomers(); break;
        case 'suppliers': loadSuppliers(); break;
        case 'payments': loadPayments(); break;
        case 'reports': loadReports(); break;
        case 'users': loadUsers(); break;
    }
}

// ---------------------------------------------------------
// API FETCH HELPER
// ---------------------------------------------------------
async function apiFetch(endpoint, options = {}) {
    options.headers = options.headers || {};
    options.headers['Authorization'] = `Bearer ${authToken}`;
    options.headers['Content-Type'] = 'application/json';

    const res = await fetch(`${API_BASE}${endpoint}`, options);
    if (res.status === 401) {
        logout();
        throw new Error('Unauthorized');
    }
    const data = await res.json();
    if (!res.ok) {
        throw new Error(data.detail || 'API Error');
    }
    return data;
}

// ---------------------------------------------------------
// DASHBOARD MODULE
// ---------------------------------------------------------
async function loadDashboard() {
    try {
        const summary = await apiFetch('/dashboard/summary');
        document.getElementById('stat-total-products').innerText = summary.total_products;
        document.getElementById('stat-total-stock').innerText = summary.total_stock;
        document.getElementById('stat-low-stock').innerText = summary.low_stock_count;
        document.getElementById('stat-out-of-stock').innerText = summary.out_of_stock_count;
        document.getElementById('stat-todays-sales').innerText = `$${summary.todays_sales.toFixed(2)}`;
        document.getElementById('stat-sales-profit').innerText = `$${summary.sales_profit.toFixed(2)}`;
        document.getElementById('stat-receivables').innerText = `$${summary.customer_receivables.toFixed(2)}`;
        document.getElementById('stat-payables').innerText = `$${summary.supplier_payables.toFixed(2)}`;

        const lowStockItems = await apiFetch('/inventory/low-stock');
        const tbody = document.querySelector('#table-dash-lowstock tbody');
        tbody.innerHTML = '';
        lowStockItems.forEach(item => {
            tbody.innerHTML += `
                <tr>
                    <td><code>${item.sku}</code></td>
                    <td><strong>${item.product_name}</strong></td>
                    <td><span class="tag orange">${item.quantity_on_hand}</span></td>
                    <td>${item.reorder_level}</td>
                    <td><span class="tag orange">LOW STOCK</span></td>
                </tr>
            `;
        });
    } catch (err) {
        console.error(err);
    }
}

// ---------------------------------------------------------
// PRODUCTS MODULE
// ---------------------------------------------------------
async function loadProducts() {
    try {
        allProducts = await apiFetch('/products');
        renderProductsTable(allProducts);
    } catch (err) {
        console.error(err);
    }
}

function renderProductsTable(products) {
    const tbody = document.querySelector('#table-products tbody');
    tbody.innerHTML = '';
    products.forEach(p => {
        const statusTag = p.stock_quantity > p.min_stock_alert 
            ? '<span class="tag green">IN STOCK</span>'
            : (p.stock_quantity > 0 ? '<span class="tag orange">LOW STOCK</span>' : '<span class="tag red">OUT OF STOCK</span>');

        tbody.innerHTML += `
            <tr>
                <td><code>${p.sku}</code></td>
                <td><strong>${p.name}</strong></td>
                <td>${p.category_id || 'General'}</td>
                <td>$${p.cost_price.toFixed(2)}</td>
                <td>$${p.selling_price.toFixed(2)}</td>
                <td>${p.stock_quantity} ${statusTag}</td>
                <td>
                    <button class="chip-btn" onclick="deactivateProduct(${p.id})"><i class="fa-solid fa-trash"></i></button>
                </td>
            </tr>
        `;
    });
}

function filterProducts() {
    const query = document.getElementById('search-products').value.toLowerCase();
    const filtered = allProducts.filter(p => 
        p.name.toLowerCase().includes(query) || 
        p.sku.toLowerCase().includes(query) ||
        (p.barcode && p.barcode.toLowerCase().includes(query))
    );
    renderProductsTable(filtered);
}

function openProductModal() {
    if (!hasPermission('Products', 'FULL')) {
        alert('You do not have permission to add products.');
        return;
    }
    document.getElementById('product-modal').classList.add('active');
}

async function handleCreateProduct(e) {
    e.preventDefault();
    const payload = {
        sku: document.getElementById('p-sku').value,
        barcode: document.getElementById('p-barcode').value || null,
        name: document.getElementById('p-name').value,
        cost_price: parseFloat(document.getElementById('p-cost').value),
        selling_price: parseFloat(document.getElementById('p-price').value),
        initial_stock: parseFloat(document.getElementById('p-initial-stock').value),
        min_stock_alert: parseInt(document.getElementById('p-alert').value)
    };

    try {
        await apiFetch('/products', { method: 'POST', body: JSON.stringify(payload) });
        closeModal('product-modal');
        loadProducts();
    } catch (err) {
        alert(err.message);
    }
}

// ---------------------------------------------------------
// INVENTORY MODULE
// ---------------------------------------------------------
async function loadInventory() {
    try {
        const movements = await apiFetch('/inventory/movements');
        const tbody = document.querySelector('#table-movements tbody');
        tbody.innerHTML = '';
        movements.forEach(m => {
            const isAdd = m.movement_type.includes('IN') || m.movement_type.includes('RECEIVE');
            const color = isAdd ? 'green' : 'red';
            tbody.innerHTML += `
                <tr>
                    <td>${new Date(m.created_at).toLocaleString()}</td>
                    <td><strong>${m.product_name}</strong></td>
                    <td><span class="tag ${color}">${m.movement_type}</span></td>
                    <td><strong>${isAdd ? '+' : '-'}${m.quantity}</strong></td>
                    <td><code>${m.reference_number || 'N/A'}</code></td>
                </tr>
            `;
        });

        allProducts = await apiFetch('/products');
        const select = document.getElementById('adj-product-id');
        select.innerHTML = '';
        allProducts.forEach(p => {
            select.innerHTML += `<option value="${p.id}">${p.sku} - ${p.name} (Qty: ${p.stock_quantity})</option>`;
        });

    } catch (err) {
        console.error(err);
    }
}

function openAdjustmentModal() {
    if (!hasPermission('Inventory', 'FULL')) {
        alert('You do not have permission to adjust inventory.');
        return;
    }
    document.getElementById('adjustment-modal').classList.add('active');
}

async function handleStockAdjustment(e) {
    e.preventDefault();
    const payload = {
        product_id: parseInt(document.getElementById('adj-product-id').value),
        adjustment_type: document.getElementById('adj-type').value,
        quantity: parseFloat(document.getElementById('adj-qty').value),
        reason: document.getElementById('adj-reason').value
    };

    try {
        await apiFetch('/inventory/adjust', { method: 'POST', body: JSON.stringify(payload) });
        closeModal('adjustment-modal');
        loadInventory();
    } catch (err) {
        alert(err.message);
    }
}

// ---------------------------------------------------------
// SALES POS MODULE
// ---------------------------------------------------------
async function loadSalesPOS() {
    try {
        allProducts = await apiFetch('/products');
        allCustomers = await apiFetch('/customers');

        const custSelect = document.getElementById('pos-customer-select');
        custSelect.innerHTML = '<option value="">Walk-in Customer</option>';
        allCustomers.forEach(c => {
            custSelect.innerHTML += `<option value="${c.id}">${c.name} (Bal: $${c.current_balance})</option>`;
        });

        const grid = document.getElementById('pos-products-grid');
        grid.innerHTML = '';
        allProducts.forEach(p => {
            grid.innerHTML += `
                <div class="product-item-card" onclick="addToPOSCart(${p.id})">
                    <h5>${p.name}</h5>
                    <div class="price">$${p.selling_price.toFixed(2)}</div>
                    <div class="stock-tag">Stock: ${p.stock_quantity}</div>
                </div>
            `;
        });

        renderPOSCart();

    } catch (err) {
        console.error(err);
    }
}

function addToPOSCart(productId) {
    const product = allProducts.find(p => p.id === productId);
    if (!product) return;

    if (product.stock_quantity <= 0) {
        alert('Product is out of stock!');
        return;
    }

    const existing = posCart.find(item => item.product_id === productId);
    if (existing) {
        if (existing.quantity + 1 > product.stock_quantity) {
            alert('Cannot add more than available stock.');
            return;
        }
        existing.quantity += 1;
    } else {
        posCart.push({
            product_id: product.id,
            name: product.name,
            unit_price: product.selling_price,
            quantity: 1
        });
    }
    renderPOSCart();
}

function updateCartQty(productId, delta) {
    const item = posCart.find(i => i.product_id === productId);
    if (!item) return;

    item.quantity += delta;
    if (item.quantity <= 0) {
        posCart = posCart.filter(i => i.product_id !== productId);
    }
    renderPOSCart();
}

function renderPOSCart() {
    const container = document.getElementById('pos-cart-items');
    if (posCart.length === 0) {
        container.innerHTML = '<div class="empty-cart">No items added to cart</div>';
        renderCartSummary();
        return;
    }

    container.innerHTML = '';
    posCart.forEach(item => {
        container.innerHTML += `
            <div class="cart-item">
                <div class="cart-item-info">
                    <h6>${item.name}</h6>
                    <small>$${item.unit_price.toFixed(2)} x ${item.quantity}</small>
                </div>
                <div class="cart-item-qty">
                    <button onclick="updateCartQty(${item.product_id}, -1)">-</button>
                    <span>${item.quantity}</span>
                    <button onclick="updateCartQty(${item.product_id}, 1)">+</button>
                </div>
            </div>
        `;
    });
    renderCartSummary();
}

function renderCartSummary() {
    let subtotal = 0;
    posCart.forEach(i => subtotal += (i.unit_price * i.quantity));
    document.getElementById('pos-subtotal').innerText = `$${subtotal.toFixed(2)}`;

    const discount = parseFloat(document.getElementById('pos-discount').value) || 0;
    const finalAmount = Math.max(0, subtotal - discount);
    document.getElementById('pos-final-amount').innerText = `$${finalAmount.toFixed(2)}`;
}

async function submitPOSSale() {
    if (posCart.length === 0) {
        alert('Cart is empty!');
        return;
    }

    const customerVal = document.getElementById('pos-customer-select').value;
    const discountVal = parseFloat(document.getElementById('pos-discount').value) || 0;
    const paidVal = parseFloat(document.getElementById('pos-paid').value) || 0;

    const payload = {
        customer_id: customerVal ? parseInt(customerVal) : null,
        discount_amount: discountVal,
        tax_amount: 0.0,
        paid_amount: paidVal,
        items: posCart.map(i => ({
            product_id: i.product_id,
            unit_price: i.unit_price,
            quantity: i.quantity
        }))
    };

    try {
        const sale = await apiFetch('/sales', { method: 'POST', body: JSON.stringify(payload) });
        alert(`Sale Completed Successfully! Invoice #: ${sale.invoice_no}`);
        posCart = [];
        document.getElementById('pos-discount').value = 0;
        document.getElementById('pos-paid').value = 0;
        loadSalesPOS();
    } catch (err) {
        alert(`Sale Error: ${err.message}`);
    }
}

// ---------------------------------------------------------
// PURCHASES MODULE
// ---------------------------------------------------------
async function loadPurchases() {
    try {
        const purchases = await apiFetch('/purchases');
        const tbody = document.querySelector('#table-purchases tbody');
        tbody.innerHTML = '';
        purchases.forEach(p => {
            tbody.innerHTML += `
                <tr>
                    <td><code>${p.purchase_no}</code></td>
                    <td><strong>${p.supplier_name}</strong></td>
                    <td>$${p.total_amount.toFixed(2)}</td>
                    <td>$${p.paid_amount.toFixed(2)}</td>
                    <td><span class="tag green">${p.status}</span></td>
                    <td>${new Date(p.created_at).toLocaleDateString()}</td>
                </tr>
            `;
        });
    } catch (err) {
        console.error(err);
    }
}

// ---------------------------------------------------------
// CUSTOMERS & SUPPLIERS MODULES
// ---------------------------------------------------------
async function loadCustomers() {
    try {
        allCustomers = await apiFetch('/customers');
        const tbody = document.querySelector('#table-customers tbody');
        tbody.innerHTML = '';
        allCustomers.forEach(c => {
            tbody.innerHTML += `
                <tr>
                    <td><strong>${c.name}</strong></td>
                    <td>${c.phone || 'N/A'}</td>
                    <td>${c.email || 'N/A'}</td>
                    <td><strong style="color: var(--accent-gold);">$${c.current_balance.toFixed(2)}</strong></td>
                </tr>
            `;
        });
    } catch (err) {
        console.error(err);
    }
}

async function loadSuppliers() {
    try {
        allSuppliers = await apiFetch('/suppliers');
        const tbody = document.querySelector('#table-suppliers tbody');
        tbody.innerHTML = '';
        allSuppliers.forEach(s => {
            tbody.innerHTML += `
                <tr>
                    <td><strong>${s.name}</strong></td>
                    <td>${s.phone || 'N/A'}</td>
                    <td>${s.email || 'N/A'}</td>
                    <td><strong style="color: var(--accent-teal);">$${s.current_balance.toFixed(2)}</strong></td>
                </tr>
            `;
        });
    } catch (err) {
        console.error(err);
    }
}

function openCustomerModal() { document.getElementById('customer-modal').classList.add('active'); }
function openSupplierModal() { document.getElementById('supplier-modal').classList.add('active'); }

async function handleCreateCustomer(e) {
    e.preventDefault();
    const payload = {
        name: document.getElementById('cust-name').value,
        phone: document.getElementById('cust-phone').value,
        email: document.getElementById('cust-email').value
    };
    try {
        await apiFetch('/customers', { method: 'POST', body: JSON.stringify(payload) });
        closeModal('customer-modal');
        loadCustomers();
    } catch (err) { alert(err.message); }
}

async function handleCreateSupplier(e) {
    e.preventDefault();
    const payload = {
        name: document.getElementById('sup-name').value,
        phone: document.getElementById('sup-phone').value,
        email: document.getElementById('sup-email').value
    };
    try {
        await apiFetch('/suppliers', { method: 'POST', body: JSON.stringify(payload) });
        closeModal('supplier-modal');
        loadSuppliers();
    } catch (err) { alert(err.message); }
}

// ---------------------------------------------------------
// PAYMENTS MODULE
// ---------------------------------------------------------
async function loadPayments() {
    try {
        const payments = await apiFetch('/payments');
        const tbody = document.querySelector('#table-payments tbody');
        tbody.innerHTML = '';
        payments.forEach(p => {
            tbody.innerHTML += `
                <tr>
                    <td><code>${p.payment_no}</code></td>
                    <td><span class="tag blue">${p.entity_type}</span></td>
                    <td>#${p.entity_id}</td>
                    <td><strong>$${p.amount.toFixed(2)}</strong></td>
                    <td>${p.payment_method}</td>
                    <td>${p.reference_no || 'N/A'}</td>
                    <td>${new Date(p.payment_date).toLocaleDateString()}</td>
                </tr>
            `;
        });
    } catch (err) {
        console.error(err);
    }
}

function openPaymentModal() {
    if (!hasPermission('Payments', 'FULL')) {
        alert('You do not have permission to record payments.');
        return;
    }
    document.getElementById('payment-modal').classList.add('active');
    populatePaymentEntities();
}

async function populatePaymentEntities() {
    const type = document.getElementById('pay-entity-type').value;
    const select = document.getElementById('pay-entity-id');
    select.innerHTML = '';

    if (type === 'CUSTOMER') {
        const customers = await apiFetch('/customers');
        customers.forEach(c => {
            select.innerHTML += `<option value="${c.id}">${c.name} (Receivable: $${c.current_balance})</option>`;
        });
    } else {
        const suppliers = await apiFetch('/suppliers');
        suppliers.forEach(s => {
            select.innerHTML += `<option value="${s.id}">${s.name} (Payable: $${s.current_balance})</option>`;
        });
    }
}

async function handlePayment(e) {
    e.preventDefault();
    const payload = {
        entity_type: document.getElementById('pay-entity-type').value,
        entity_id: parseInt(document.getElementById('pay-entity-id').value),
        amount: parseFloat(document.getElementById('pay-amount').value),
        payment_method: document.getElementById('pay-method').value
    };

    try {
        await apiFetch('/payments', { method: 'POST', body: JSON.stringify(payload) });
        closeModal('payment-modal');
        loadPayments();
    } catch (err) { alert(err.message); }
}

// ---------------------------------------------------------
// REPORTS & USERS MODULES
// ---------------------------------------------------------
async function loadReports() {
    try {
        const report = await apiFetch('/reports/stock-valuation');
        document.getElementById('report-valuation-total').innerText = `$${report.total_stock_valuation.toFixed(2)}`;
    } catch (err) { console.error(err); }
}

async function loadUsers() {
    try {
        const users = await apiFetch('/users');
        const tbody = document.querySelector('#table-users tbody');
        tbody.innerHTML = '';
        users.forEach(u => {
            tbody.innerHTML += `
                <tr>
                    <td>#${u.id}</td>
                    <td><strong>${u.name}</strong></td>
                    <td>${u.email}</td>
                    <td><span class="badge">${u.role_name}</span></td>
                    <td><span class="tag green">ACTIVE</span></td>
                </tr>
            `;
        });
    } catch (err) { console.error(err); }
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}
