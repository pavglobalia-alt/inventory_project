from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_full_system_flow():
    print("\n--- 1. Testing Super Admin Login ---")
    login_res = client.post("/api/v1/auth/login", json={
        "email": "admin@inventory.com",
        "password": "Admin@123"
    })
    assert login_res.status_code == 200, login_res.text
    admin_token = login_res.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    print("[PASS] Super Admin Login Successful")

    print("\n--- 2. Testing Salesman Login & RBAC Boundaries ---")
    salesman_res = client.post("/api/v1/auth/login", json={
        "email": "salesman@inventory.com",
        "password": "Sales@123"
    })
    assert salesman_res.status_code == 200, salesman_res.text
    salesman_token = salesman_res.json()["access_token"]
    salesman_headers = {"Authorization": f"Bearer {salesman_token}"}
    print("[PASS] Salesman Login Successful")

    # Test Salesman attempting to create a Purchase (Should return HTTP 403 Forbidden)
    forbidden_po = client.post("/api/v1/purchases", headers=salesman_headers, json={
        "supplier_id": 1,
        "items": [{"product_id": 1, "unit_cost": 50.0, "quantity": 10}]
    })
    assert forbidden_po.status_code == 403, f"Expected 403 Forbidden, got {forbidden_po.status_code}"
    assert forbidden_po.json()["detail"] == "You do not have permission to access this resource."
    print("[PASS] RBAC Enforced: Salesman restricted from creating Purchases (403 Forbidden)")

    # Test Super Admin creating Purchase on Credit (Automated total calculation and Supplier payable update)
    po_res = client.post("/api/v1/purchases", headers=admin_headers, json={
        "supplier_id": 1,
        "items": [{"product_id": 1, "unit_cost": 50.0, "quantity": 10}]
    })
    assert po_res.status_code == 200, po_res.text
    po_data = po_res.json()
    assert po_data["total_amount"] == 500.0
    assert po_data["paid_amount"] == 0.0
    print(f"[PASS] Credit Purchase Created: PO #{po_data['purchase_no']}, Total: ${po_data['total_amount']}, Paid: ${po_data['paid_amount']}")

    print("\n--- 3. Testing Products List ---")
    products_res = client.get("/api/v1/products", headers=admin_headers)
    assert products_res.status_code == 200
    products = products_res.json()
    assert len(products) >= 3
    print(f"[PASS] Products fetched successfully: Found {len(products)} products")

    print("\n--- 4. Testing POS Sale Creation & Inventory Stock Deduction ---")
    p1 = next((p for p in products if p["stock_quantity"] >= 2), products[0])
    initial_stock = p1["stock_quantity"]

    sale_res = client.post("/api/v1/sales", headers=salesman_headers, json={
        "customer_id": 1,
        "discount_amount": 0.0,
        "tax_amount": 0.0,
        "paid_amount": 99.99,
        "items": [
            {"product_id": p1["id"], "unit_price": p1["selling_price"], "quantity": 2}
        ]
    })
    assert sale_res.status_code == 200, sale_res.text
    sale_data = sale_res.json()
    assert sale_data["invoice_no"].startswith("INV-")
    print(f"[PASS] POS Sale created: Invoice #{sale_data['invoice_no']}, Total: ${sale_data['final_amount']}")

    # Verify Stock decreased by 2
    updated_p1 = client.get(f"/api/v1/products/{p1['id']}", headers=admin_headers).json()
    assert updated_p1["stock_quantity"] == initial_stock - 2
    print(f"[PASS] Stock integrity verified: {initial_stock} -> {updated_p1['stock_quantity']}")

    print("\n--- 5. Testing Dashboard Summary KPI Metrics ---")
    dash_res = client.get("/api/v1/dashboard/summary", headers=admin_headers)
    assert dash_res.status_code == 200
    dash_summary = dash_res.json()
    assert dash_summary["total_products"] > 0
    assert dash_summary["todays_sales"] > 0
    print(f"[PASS] Dashboard metrics computed: Today Sales=${dash_summary['todays_sales']}, Profit=${dash_summary['sales_profit']}")

if __name__ == "__main__":
    test_full_system_flow()
