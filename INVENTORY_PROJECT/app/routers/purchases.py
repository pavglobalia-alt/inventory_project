import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.models import (
    Purchase, PurchaseItem, Supplier, Product, Inventory, StockMovement, User
)
from app.schemas.schemas import PurchaseCreate, PurchaseOut
from app.core.permissions import require_permission

router = APIRouter(prefix="/purchases", tags=["Purchase Management"])

@router.get("", response_model=List[PurchaseOut])
def list_purchases(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("Purchases", "VIEW"))
):
    purchases = db.query(Purchase).order_by(Purchase.created_at.desc()).all()
    res = []
    for p in purchases:
        p_out = PurchaseOut.model_validate(p)
        p_out.supplier_name = p.supplier.name if p.supplier else "Unknown"
        res.append(p_out)
    return res


@router.post("", response_model=PurchaseOut)
def create_purchase(
    payload: PurchaseCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("Purchases", "FULL"))
):
    supplier = db.query(Supplier).filter(Supplier.id == payload.supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    if not payload.items:
        raise HTTPException(status_code=400, detail="Purchase order must contain at least one item")

    total_amount = 0.0
    items_to_create = []

    for item_in in payload.items:
        product = db.query(Product).filter(Product.id == item_in.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product ID {item_in.product_id} not found")

        subtotal = item_in.unit_cost * item_in.quantity
        total_amount += subtotal

        items_to_create.append({
            "product": product,
            "unit_cost": item_in.unit_cost,
            "quantity": item_in.quantity,
            "subtotal": subtotal
        })

    purchase_no = f"PO-{uuid.uuid4().hex[:8].upper()}"

    purchase = Purchase(
        purchase_no=purchase_no,
        supplier_id=supplier.id,
        total_amount=total_amount,
        paid_amount=payload.paid_amount,
        status="RECEIVED",
        created_by=user.id
    )
    db.add(purchase)
    db.flush()

    for info in items_to_create:
        p_item = PurchaseItem(
            purchase_id=purchase.id,
            product_id=info["product"].id,
            unit_cost=info["unit_cost"],
            quantity=info["quantity"],
            subtotal=info["subtotal"]
        )
        db.add(p_item)

        # Update product cost_price if new purchase price is recorded
        info["product"].cost_price = info["unit_cost"]

        # Increase inventory stock
        inventory = db.query(Inventory).filter(Inventory.product_id == info["product"].id).first()
        if not inventory:
            inventory = Inventory(product_id=info["product"].id, quantity_on_hand=0.0)
            db.add(inventory)
            db.flush()

        inventory.quantity_on_hand += info["quantity"]

        # Log Stock Movement
        sm = StockMovement(
            product_id=info["product"].id,
            movement_type="PURCHASE_RECEIVE",
            quantity=info["quantity"],
            reference_number=purchase_no,
            user_id=user.id,
            notes=f"Stock Received from Supplier {supplier.name}"
        )
        db.add(sm)

    # Update Supplier Payable Balance
    unpaid = total_amount - payload.paid_amount
    if unpaid > 0:
        supplier.current_balance += unpaid

    db.commit()
    db.refresh(purchase)

    p_out = PurchaseOut.model_validate(purchase)
    p_out.supplier_name = supplier.name
    return p_out
