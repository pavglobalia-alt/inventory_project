import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.models import (
    Sale, SaleItem, Product, Inventory, StockMovement, Customer, User, AuditLog
)
from app.schemas.schemas import SaleCreate, SaleOut
from app.core.permissions import require_permission

router = APIRouter(prefix="/sales", tags=["Sales Management"])

@router.get("", response_model=List[SaleOut])
def list_sales(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("Sales", "VIEW"))
):
    sales = db.query(Sale).order_by(Sale.created_at.desc()).all()
    res = []
    for s in sales:
        s_out = SaleOut.model_validate(s)
        s_out.customer_name = s.customer.name if s.customer else "Walk-in Customer"
        s_out.salesman_name = s.salesman.name if s.salesman else "System"
        res.append(s_out)
    return res


@router.get("/{sale_id}")
def get_sale_details(
    sale_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("Sales", "VIEW"))
):
    sale = db.query(Sale).filter(Sale.id == sale_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale transaction not found")

    items_data = []
    for item in sale.items:
        items_data.append({
            "product_id": item.product_id,
            "product_sku": item.product.sku,
            "product_name": item.product.name,
            "unit_price": item.unit_price,
            "quantity": item.quantity,
            "subtotal": item.subtotal
        })

    return {
        "id": sale.id,
        "invoice_no": sale.invoice_no,
        "customer_id": sale.customer_id,
        "customer_name": sale.customer.name if sale.customer else "Walk-in Customer",
        "salesman_name": sale.salesman.name if sale.salesman else "N/A",
        "total_amount": sale.total_amount,
        "discount_amount": sale.discount_amount,
        "tax_amount": sale.tax_amount,
        "final_amount": sale.final_amount,
        "paid_amount": sale.paid_amount,
        "payment_status": sale.payment_status,
        "created_at": sale.created_at,
        "items": items_data
    }


@router.post("", response_model=SaleOut)
def create_sale(
    payload: SaleCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("Sales", "LIMITED"))
):
    if not payload.items:
        raise HTTPException(status_code=400, detail="Sale must contain at least one item")

    # Salesman restrictions check
    is_salesman = user.role and user.role.name == "Salesman"

    total_gross = 0.0
    total_profit = 0.0
    items_to_create = []

    # Atomic transaction process
    for item_in in payload.items:
        product = db.query(Product).filter(Product.id == item_in.product_id, Product.is_active == True).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product ID {item_in.product_id} not found")

        inventory = db.query(Inventory).filter(Inventory.product_id == product.id).first()
        if not inventory or inventory.quantity_on_hand < item_in.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for product '{product.name}'. Available: {inventory.quantity_on_hand if inventory else 0}"
            )

        # Enforcement: Salesman cannot modify catalog selling price
        unit_price = item_in.unit_price
        if is_salesman and abs(unit_price - product.selling_price) > 0.01:
            raise HTTPException(
                status_code=403,
                detail=f"Salesman is not authorized to alter selling price for '{product.name}'."
            )

        subtotal = unit_price * item_in.quantity
        profit = (unit_price - product.cost_price) * item_in.quantity

        total_gross += subtotal
        total_profit += profit

        items_to_create.append({
            "product": product,
            "inventory": inventory,
            "unit_price": unit_price,
            "cost_price": product.cost_price,
            "quantity": item_in.quantity,
            "subtotal": subtotal,
            "profit": profit
        })

    # Discount enforcement
    if is_salesman and payload.discount_amount > (total_gross * 0.05):  # Max 5% for salesman without admin approval
        raise HTTPException(status_code=403, detail="Salesman cannot grant discount greater than 5%.")

    final_amount = (total_gross - payload.discount_amount) + payload.tax_amount
    invoice_no = f"INV-{uuid.uuid4().hex[:8].upper()}"

    # Determine payment status
    if payload.paid_amount >= final_amount:
        p_status = "PAID"
    elif payload.paid_amount > 0:
        p_status = "PARTIAL"
    else:
        p_status = "UNPAID"

    # Create Sale
    sale = Sale(
        invoice_no=invoice_no,
        customer_id=payload.customer_id,
        salesman_id=user.id,
        total_amount=total_gross,
        discount_amount=payload.discount_amount,
        tax_amount=payload.tax_amount,
        final_amount=final_amount,
        paid_amount=payload.paid_amount,
        payment_status=p_status
    )
    db.add(sale)
    db.flush()

    # Process items and inventory
    for item_info in items_to_create:
        s_item = SaleItem(
            sale_id=sale.id,
            product_id=item_info["product"].id,
            unit_price=item_info["unit_price"],
            cost_price=item_info["cost_price"],
            quantity=item_info["quantity"],
            subtotal=item_info["subtotal"],
            profit=item_info["profit"]
        )
        db.add(s_item)

        # Deduct stock
        item_info["inventory"].quantity_on_hand -= item_info["quantity"]

        # Stock Movement
        sm = StockMovement(
            product_id=item_info["product"].id,
            movement_type="SALE_DEDUCT",
            quantity=item_info["quantity"],
            reference_number=invoice_no,
            user_id=user.id,
            notes=f"Sale Invoice #{invoice_no}"
        )
        db.add(sm)

    # Customer Balance update (Receivable)
    unpaid_balance = final_amount - payload.paid_amount
    if payload.customer_id and unpaid_balance > 0:
        customer = db.query(Customer).filter(Customer.id == payload.customer_id).first()
        if customer:
            customer.current_balance += unpaid_balance

    db.commit()
    db.refresh(sale)

    s_out = SaleOut.model_validate(sale)
    s_out.customer_name = sale.customer.name if sale.customer else "Walk-in Customer"
    s_out.salesman_name = user.name
    return s_out
