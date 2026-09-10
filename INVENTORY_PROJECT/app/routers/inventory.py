from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.models import Inventory, Product, StockMovement, StockAdjustment, User, AuditLog
from app.schemas.schemas import StockAdjustmentCreate, StockMovementOut
from app.core.permissions import require_permission

router = APIRouter(prefix="/inventory", tags=["Inventory Management"])

@router.get("/stock")
def get_stock_list(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("Inventory", "VIEW"))
):
    items = db.query(Inventory).join(Product).filter(Product.is_active == True).all()
    result = []
    for item in items:
        result.append({
            "id": item.id,
            "product_id": item.product_id,
            "sku": item.product.sku,
            "barcode": item.product.barcode,
            "product_name": item.product.name,
            "category": item.product.category.name if item.product.category else "N/A",
            "quantity_on_hand": item.quantity_on_hand,
            "reorder_level": item.reorder_level,
            "cost_price": item.product.cost_price,
            "stock_value": item.quantity_on_hand * item.product.cost_price,
            "status": "OUT_OF_STOCK" if item.quantity_on_hand <= 0 else ("LOW_STOCK" if item.quantity_on_hand <= item.reorder_level else "IN_STOCK")
        })
    return result


@router.get("/low-stock")
def get_low_stock(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("Inventory", "VIEW"))
):
    items = db.query(Inventory).join(Product).filter(
        Product.is_active == True,
        Inventory.quantity_on_hand <= Inventory.reorder_level,
        Inventory.quantity_on_hand > 0
    ).all()

    return [{
        "product_id": i.product_id,
        "product_name": i.product.name,
        "sku": i.product.sku,
        "quantity_on_hand": i.quantity_on_hand,
        "reorder_level": i.reorder_level
    } for i in items]


@router.get("/out-of-stock")
def get_out_of_stock(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("Inventory", "VIEW"))
):
    items = db.query(Inventory).join(Product).filter(
        Product.is_active == True,
        Inventory.quantity_on_hand <= 0
    ).all()

    return [{
        "product_id": i.product_id,
        "product_name": i.product.name,
        "sku": i.product.sku,
        "quantity_on_hand": i.quantity_on_hand
    } for i in items]


@router.get("/movements", response_model=List[StockMovementOut])
def get_stock_movements(
    limit: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("Inventory", "VIEW"))
):
    movements = db.query(StockMovement).order_by(StockMovement.created_at.desc()).limit(limit).all()
    res = []
    for m in movements:
        m_out = StockMovementOut.model_validate(m)
        m_out.product_name = m.product.name if m.product else "N/A"
        res.append(m_out)
    return res


@router.post("/adjust")
def adjust_stock(
    payload: StockAdjustmentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("Inventory", "FULL"))
):
    inventory = db.query(Inventory).filter(Inventory.product_id == payload.product_id).first()
    if not inventory:
        raise HTTPException(status_code=404, detail="Product inventory record not found")

    old_qty = inventory.quantity_on_hand
    if payload.adjustment_type.upper() == "IN":
        new_qty = old_qty + payload.quantity
        m_type = "ADJUSTMENT_IN"
    elif payload.adjustment_type.upper() == "OUT":
        if old_qty < payload.quantity:
            raise HTTPException(status_code=400, detail="Cannot adjust stock out below zero")
        new_qty = old_qty - payload.quantity
        m_type = "ADJUSTMENT_OUT"
    else:
        raise HTTPException(status_code=400, detail="Invalid adjustment type (must be IN or OUT)")

    inventory.quantity_on_hand = new_qty

    # Record Adjustment Log
    adj = StockAdjustment(
        product_id=payload.product_id,
        adjustment_type=payload.adjustment_type.upper(),
        quantity=payload.quantity,
        reason=payload.reason,
        user_id=user.id
    )
    db.add(adj)

    # Record Movement
    movement = StockMovement(
        product_id=payload.product_id,
        movement_type=m_type,
        quantity=payload.quantity,
        reference_number="STK-ADJ",
        user_id=user.id,
        notes=payload.reason
    )
    db.add(movement)

    # Audit log entry
    audit = AuditLog(
        user_id=user.id,
        action="STOCK_ADJUSTMENT",
        module="Inventory",
        record_id=payload.product_id,
        old_value={"quantity_on_hand": old_qty},
        new_value={"quantity_on_hand": new_qty, "reason": payload.reason}
    )
    db.add(audit)

    db.commit()
    return {"message": "Stock adjusted successfully", "new_quantity": new_qty}
