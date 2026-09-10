from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.database import get_db
from app.models.models import (
    Product, Inventory, Sale, SaleItem, Purchase, Customer, Supplier, Payment, User
)
from app.schemas.schemas import DashboardSummary
from app.core.permissions import require_permission

router = APIRouter(tags=["Reports & Dashboard"])

@router.get("/dashboard/summary", response_model=DashboardSummary)
def get_dashboard_summary(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("Dashboard", "VIEW"))
):
    # Total Active Products
    total_products = db.query(func.count(Product.id)).filter(Product.is_active == True).scalar() or 0

    # Stock metrics
    stock_stats = db.query(
        func.coalesce(func.sum(Inventory.quantity_on_hand), 0.0)
    ).join(Product).filter(Product.is_active == True).scalar() or 0.0

    low_stock_count = db.query(func.count(Inventory.id)).join(Product).filter(
        Product.is_active == True,
        Inventory.quantity_on_hand <= Inventory.reorder_level,
        Inventory.quantity_on_hand > 0
    ).scalar() or 0

    out_of_stock_count = db.query(func.count(Inventory.id)).join(Product).filter(
        Product.is_active == True,
        Inventory.quantity_on_hand <= 0
    ).scalar() or 0

    # Today's Sales
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    todays_sales = db.query(func.coalesce(func.sum(Sale.final_amount), 0.0)).filter(
        Sale.created_at >= today_start
    ).scalar() or 0.0

    # Today's Purchases
    todays_purchases = db.query(func.coalesce(func.sum(Purchase.total_amount), 0.0)).filter(
        Purchase.created_at >= today_start
    ).scalar() or 0.0

    # Profit calculation
    sales_profit = db.query(func.coalesce(func.sum(SaleItem.profit), 0.0)).scalar() or 0.0

    # Financial Ledgers
    customer_receivables = db.query(func.coalesce(func.sum(Customer.current_balance), 0.0)).filter(Customer.is_active == True).scalar() or 0.0
    supplier_payables = db.query(func.coalesce(func.sum(Supplier.current_balance), 0.0)).filter(Supplier.is_active == True).scalar() or 0.0

    total_customers = db.query(func.count(Customer.id)).filter(Customer.is_active == True).scalar() or 0
    total_suppliers = db.query(func.count(Supplier.id)).filter(Supplier.is_active == True).scalar() or 0

    pending_payments = customer_receivables + supplier_payables

    return DashboardSummary(
        total_products=total_products,
        total_stock=stock_stats,
        low_stock_count=low_stock_count,
        out_of_stock_count=out_of_stock_count,
        todays_sales=todays_sales,
        todays_purchases=todays_purchases,
        pending_payments=pending_payments,
        total_customers=total_customers,
        total_suppliers=total_suppliers,
        sales_profit=sales_profit,
        customer_receivables=customer_receivables,
        supplier_payables=supplier_payables
    )


@router.get("/reports/stock-valuation")
def get_stock_valuation_report(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("Reports", "VIEW"))
):
    items = db.query(Inventory).join(Product).filter(Product.is_active == True).all()
    total_valuation = 0.0
    details = []

    for item in items:
        val = item.quantity_on_hand * item.product.cost_price
        total_valuation += val
        details.append({
            "product_id": item.product_id,
            "sku": item.product.sku,
            "name": item.product.name,
            "quantity": item.quantity_on_hand,
            "unit_cost": item.product.cost_price,
            "total_value": val
        })

    return {
        "total_stock_valuation": total_valuation,
        "items": details
    }
