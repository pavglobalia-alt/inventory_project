from sqlalchemy.orm import Session
from app.db.database import Base, engine, SessionLocal
from app.models.models import (
    Role, Permission, RolePermission, User,
    Category, Brand, Unit, Product, Inventory, StockMovement, Customer, Supplier
)
from app.core.security import get_password_hash

import sys

def seed_database(reset: bool = False):
    if reset or "--reset" in sys.argv:
        print("[INFO] Re-creating database schema...")
        Base.metadata.drop_all(bind=engine)

    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    try:
        # Check if already seeded
        if not (reset or "--reset" in sys.argv) and db.query(Role).first():
            print("[INFO] Database already seeded.")
            return

        print("[INFO] Seeding DB with RBAC matrix, Master Data & Default Users...")

        # 1. Define Modules & Actions
        modules = [
            "Dashboard", "Products", "Inventory", "Categories", 
            "Suppliers", "Purchases", "Sales", "Customers", 
            "Reports", "Users", "Payments"
        ]
        actions = ["FULL", "VIEW", "LIMITED", "DENY"]

        permissions_map = {}
        for mod in modules:
            for act in actions:
                if act != "DENY":
                    perm = Permission(module=mod, action=act, description=f"{act} permission on {mod}")
                    db.add(perm)
                    db.flush()
                    permissions_map[f"{mod}:{act}"] = perm.id

        # 2. Create Roles
        roles_data = [
            ("Super Admin", "Full control over all modules, users, roles, permissions, transactions and reports."),
            ("Sub Admin", "Operational access with sales capability and read-only access to selected master data."),
            ("Salesman", "Sales-focused access with restricted customer/price modification capabilities."),
            ("Stock Manager", "Controls products, inventory and purchasing operations."),
            ("Finance Manager", "Controls payment and financial operations with read-only operational view.")
        ]

        roles_dict = {}
        for r_name, r_desc in roles_data:
            role = Role(name=r_name, description=r_desc)
            db.add(role)
            db.flush()
            roles_dict[r_name] = role

        # 3. Map Role Permissions according to Section 14 RBAC Matrix
        # Super Admin gets FULL on everything
        for mod in modules:
            rp = RolePermission(role_id=roles_dict["Super Admin"].id, permission_id=permissions_map[f"{mod}:FULL"])
            db.add(rp)

        # Sub Admin
        sub_admin_matrix = {
            "Dashboard": "FULL", "Products": "VIEW", "Inventory": "VIEW",
            "Categories": "VIEW", "Sales": "FULL", "Customers": "VIEW", "Reports": "VIEW"
        }
        for mod, act in sub_admin_matrix.items():
            rp = RolePermission(role_id=roles_dict["Sub Admin"].id, permission_id=permissions_map[f"{mod}:{act}"])
            db.add(rp)

        # Salesman
        salesman_matrix = {
            "Dashboard": "FULL", "Products": "VIEW", "Inventory": "VIEW",
            "Categories": "VIEW", "Sales": "LIMITED", "Customers": "VIEW", "Reports": "VIEW"
        }
        for mod, act in salesman_matrix.items():
            rp = RolePermission(role_id=roles_dict["Salesman"].id, permission_id=permissions_map[f"{mod}:{act}"])
            db.add(rp)

        # Stock Manager
        stock_matrix = {
            "Dashboard": "FULL", "Products": "FULL", "Inventory": "FULL",
            "Categories": "VIEW", "Suppliers": "VIEW", "Purchases": "FULL",
            "Customers": "VIEW", "Reports": "VIEW"
        }
        for mod, act in stock_matrix.items():
            rp = RolePermission(role_id=roles_dict["Stock Manager"].id, permission_id=permissions_map[f"{mod}:{act}"])
            db.add(rp)

        # Finance Manager
        finance_matrix = {
            "Dashboard": "FULL", "Products": "VIEW", "Inventory": "VIEW",
            "Categories": "VIEW", "Suppliers": "VIEW", "Customers": "VIEW",
            "Reports": "VIEW", "Payments": "FULL"
        }
        for mod, act in finance_matrix.items():
            rp = RolePermission(role_id=roles_dict["Finance Manager"].id, permission_id=permissions_map[f"{mod}:{act}"])
            db.add(rp)

        db.flush()

        # 4. Create Default Demo Users
        users_seed = [
            ("Super Admin", "admin", "admin@inventory.com", "Admin@123", "Super Admin"),
            ("Sub Admin User", "subadmin", "subadmin@inventory.com", "Sub@123", "Sub Admin"),
            ("Sales Representative", "salesman", "salesman@inventory.com", "Sales@123", "Salesman"),
            ("Warehouse Manager", "stock", "stock@inventory.com", "Stock@123", "Stock Manager"),
            ("Accounts Officer", "finance", "finance@inventory.com", "Finance@123", "Finance Manager"),
        ]

        for u_name, u_user, u_email, u_pwd, u_role in users_seed:
            user = User(
                name=u_name,
                username=u_user,
                email=u_email,
                password_hash=get_password_hash(u_pwd),
                role_id=roles_dict[u_role].id,
                phone_no="555-0000",
                address="Default Address",
                gender="Not Specified",
                is_active=True
            )
            db.add(user)

        # 5. Master Data Setup
        cat1 = Category(name="Electronics", description="Gadgets, Accessories & Devices")
        cat2 = Category(name="Office Supplies", description="Paper, Stationery & Desk Items")
        db.add_all([cat1, cat2])

        brand1 = Brand(name="Logitech")
        brand2 = Brand(name="Dell")
        db.add_all([brand1, brand2])

        unit1 = Unit(name="Pieces", short_name="pcs")
        unit2 = Unit(name="Boxes", short_name="box")
        db.add_all([unit1, unit2])

        db.flush()

        # Sample Stakeholders
        sup1 = Supplier(name="Tech Distributors Inc", phone="+1 555-0192", email="orders@techdist.com", address="742 Evergreen Terrace", current_balance=1250.0)
        cust1 = Customer(name="Acme Corporation", phone="+1 555-4321", email="billing@acme.com", address="100 Business Park", current_balance=450.0)
        db.add_all([sup1, cust1])

        db.flush()

        # Sample Products & Initial Stock
        p1 = Product(
            sku="SKU-LOG-M100", barcode="890123456701", name="Logitech MX Master 3S Mouse",
            description="Wireless Performance Mouse", category_id=cat1.id, brand_id=brand1.id, unit_id=unit1.id,
            cost_price=75.0, selling_price=99.99, min_stock_alert=5
        )
        p2 = Product(
            sku="SKU-DEL-KB216", barcode="890123456702", name="Dell KB216 Wired Keyboard",
            description="Multimedia Keyboard - Black", category_id=cat1.id, brand_id=brand2.id, unit_id=unit1.id,
            cost_price=12.50, selling_price=19.99, min_stock_alert=8
        )
        p3 = Product(
            sku="SKU-OFF-PPR-A4", barcode="890123456703", name="A4 Copy Paper Box (5 Reams)",
            description="High Quality 80GSM White Paper", category_id=cat2.id, brand_id=None, unit_id=unit2.id,
            cost_price=22.0, selling_price=32.00, min_stock_alert=15
        )
        db.add_all([p1, p2, p3])
        db.flush()

        # Initial Inventory
        inv1 = Inventory(product_id=p1.id, quantity_on_hand=45.0, reorder_level=5.0)
        inv2 = Inventory(product_id=p2.id, quantity_on_hand=3.0, reorder_level=8.0)  # Low stock!
        inv3 = Inventory(product_id=p3.id, quantity_on_hand=0.0, reorder_level=15.0) # Out of stock!
        db.add_all([inv1, inv2, inv3])

        # Stock Movement log
        sm1 = StockMovement(product_id=p1.id, movement_type="INITIAL_STOCK", quantity=45.0, reference_number="SYS-INIT", notes="System initialization stock")
        sm2 = StockMovement(product_id=p2.id, movement_type="INITIAL_STOCK", quantity=3.0, reference_number="SYS-INIT", notes="System initialization stock")
        db.add_all([sm1, sm2])

        db.commit()
        print("[SUCCESS] Database successfully seeded!")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Database seeding failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
