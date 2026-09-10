from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.models import Customer, Supplier, User
from app.schemas.schemas import CustomerCreate, CustomerOut, SupplierCreate, SupplierOut
from app.core.permissions import require_permission

router = APIRouter(tags=["Stakeholders"])

# ---------------------------------------------------------
# Customers
# ---------------------------------------------------------
@router.get("/customers", response_model=List[CustomerOut])
def list_customers(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("Customers", "VIEW"))
):
    return db.query(Customer).filter(Customer.is_active == True).all()


@router.post("/customers", response_model=CustomerOut)
def create_customer(
    payload: CustomerCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("Customers", "FULL"))
):
    customer = Customer(**payload.model_dump())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


# ---------------------------------------------------------
# Suppliers
# ---------------------------------------------------------
@router.get("/suppliers", response_model=List[SupplierOut])
def list_suppliers(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("Suppliers", "VIEW"))
):
    return db.query(Supplier).filter(Supplier.is_active == True).all()


@router.post("/suppliers", response_model=SupplierOut)
def create_supplier(
    payload: SupplierCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("Suppliers", "FULL"))
):
    supplier = Supplier(**payload.model_dump())
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier
