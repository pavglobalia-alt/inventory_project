import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.models import Payment, Customer, Supplier, User, AuditLog
from app.schemas.schemas import PaymentCreate, PaymentOut
from app.core.permissions import require_permission

router = APIRouter(prefix="/payments", tags=["Payment Management"])

@router.get("", response_model=List[PaymentOut])
def list_payments(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("Payments", "VIEW"))
):
    payments = db.query(Payment).order_by(Payment.created_at.desc()).all()
    return payments


@router.post("", response_model=PaymentOut)
def record_payment(
    payload: PaymentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("Payments", "FULL"))
):
    entity_type = payload.entity_type.upper()
    if entity_type not in ["CUSTOMER", "SUPPLIER"]:
        raise HTTPException(status_code=400, detail="Entity type must be CUSTOMER or SUPPLIER")

    if payload.amount <= 0:
        raise HTTPException(status_code=400, detail="Payment amount must be greater than 0")

    payment_no = f"PAY-{uuid.uuid4().hex[:8].upper()}"

    if entity_type == "CUSTOMER":
        customer = db.query(Customer).filter(Customer.id == payload.entity_id).first()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        # Payment reduces Customer Receivable balance
        customer.current_balance = max(0.0, customer.current_balance - payload.amount)

    elif entity_type == "SUPPLIER":
        supplier = db.query(Supplier).filter(Supplier.id == payload.entity_id).first()
        if not supplier:
            raise HTTPException(status_code=404, detail="Supplier not found")
        # Payment reduces Supplier Payable balance
        supplier.current_balance = max(0.0, supplier.current_balance - payload.amount)

    payment = Payment(
        payment_no=payment_no,
        entity_type=entity_type,
        entity_id=payload.entity_id,
        reference_no=payload.reference_no,
        amount=payload.amount,
        payment_method=payload.payment_method,
        notes=payload.notes,
        user_id=user.id
    )
    db.add(payment)

    audit = AuditLog(
        user_id=user.id,
        action="PAYMENT_RECORDED",
        module="Payments",
        record_id=payment.id,
        new_value={"entity_type": entity_type, "entity_id": payload.entity_id, "amount": payload.amount}
    )
    db.add(audit)

    db.commit()
    db.refresh(payment)

    return payment
