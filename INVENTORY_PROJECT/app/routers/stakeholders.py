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


@router.put("/customers/{customer_id}", response_model=CustomerOut)
def update_customer(
    customer_id: int,
    payload: CustomerCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("Customers", "FULL"))
):
    customer = db.query(Customer).filter(Customer.id == customer_id, Customer.is_active == True).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    for key, value in payload.model_dump().items():
        setattr(customer, key, value)
    
    db.commit()
    db.refresh(customer)
    return customer


@router.delete("/customers/{customer_id}")
def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("Customers", "FULL"))
):
    customer = db.query(Customer).filter(Customer.id == customer_id, Customer.is_active == True).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    customer.is_active = False
    db.commit()
    return {"detail": "Customer deleted successfully"}


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


@router.put("/suppliers/{supplier_id}", response_model=SupplierOut)
def update_supplier(
    supplier_id: int,
    payload: SupplierCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("Suppliers", "FULL"))
):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id, Supplier.is_active == True).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    for key, value in payload.model_dump().items():
        setattr(supplier, key, value)
    
    db.commit()
    db.refresh(supplier)
    return supplier


@router.delete("/suppliers/{supplier_id}")
def delete_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("Suppliers", "FULL"))
):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id, Supplier.is_active == True).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    supplier.is_active = False
    db.commit()
    return {"detail": "Supplier deleted successfully"}

