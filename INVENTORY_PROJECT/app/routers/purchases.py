import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.models import (
    Purchase, PurchaseItem, Supplier, Product, Inventory, StockMovement, User
)
from app.schemas.schemas import PurchaseCreate, PurchaseOut, PurchaseItemOut
from app.core.permissions import require_permission

router = APIRouter(prefix="/purchases", tags=["Purchase Management"])

def format_purchase_out(purchase: Purchase) -> PurchaseOut:
    p_out = PurchaseOut.model_validate(purchase)
    p_out.supplier_name = purchase.supplier.name if purchase.supplier else "Unknown"
    p_out.items = [
        PurchaseItemOut(
            id=item.id,
            product_id=item.product_id,
            product_name=item.product.name if item.product else None,
            unit_cost=item.unit_cost,
            quantity=item.quantity,
            subtotal=item.subtotal
        )
        for item in purchase.items
    ]
    return p_out


@router.get("", response_model=List[PurchaseOut])
def list_purchases(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("Purchases", "VIEW"))
):
    purchases = db.query(Purchase).order_by(Purchase.created_at.desc()).all()
    return [format_purchase_out(p) for p in purchases]


@router.get("/{purchase_id}", response_model=PurchaseOut)
def get_purchase(
    purchase_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("Purchases", "VIEW"))
):
    purchase = db.query(Purchase).filter(Purchase.id == purchase_id).first()
    if not purchase:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return format_purchase_out(purchase)


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

        # Use provided unit_cost or automatically use product.cost_price
        unit_cost = item_in.unit_cost if item_in.unit_cost is not None else product.cost_price
        subtotal = unit_cost * item_in.quantity
        total_amount += subtotal

        items_to_create.append({
            "product": product,
            "unit_cost": unit_cost,
            "quantity": item_in.quantity,
            "subtotal": subtotal
        })

    purchase_no = f"PO-{uuid.uuid4().hex[:8].upper()}"

    purchase = Purchase(
        purchase_no=purchase_no,
        supplier_id=supplier.id,
        total_amount=total_amount,
        paid_amount=0.0,
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

    # Update Supplier Payable Balance (Credit Purchase)
    supplier.current_balance += total_amount

    db.commit()
    db.refresh(purchase)

    return format_purchase_out(purchase)
