from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.models import Product, Category, Brand, Unit, Inventory, StockMovement, User
from app.schemas.schemas import (
    ProductCreate, ProductOut, CategoryCreate, CategoryOut,
    BrandCreate, BrandOut, UnitCreate, UnitOut
)
from app.core.permissions import require_permission, get_current_user

router = APIRouter(prefix="/products", tags=["Product Management"])

# ---------------------------------------------------------
# Master Options: Categories, Brands, Units
# ---------------------------------------------------------
@router.get("/categories", response_model=List[CategoryOut])
def list_categories(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("Categories", "VIEW"))
):
    return db.query(Category).all()

@router.post("/categories", response_model=CategoryOut)
def create_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("Categories", "FULL"))
):
    category = Category(**payload.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category

@router.get("/brands", response_model=List[BrandOut])
def list_brands(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("Products", "VIEW"))
):
    return db.query(Brand).all()

@router.get("/units", response_model=List[UnitOut])
def list_units(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("Products", "VIEW"))
):
    return db.query(Unit).all()

# ---------------------------------------------------------
# Products CRUD
# ---------------------------------------------------------
@router.get("", response_model=List[ProductOut])
def list_products(
    search: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("Products", "VIEW"))
):
    query = db.query(Product).filter(Product.is_active == True)
    if search:
        query = query.filter(
            (Product.name.ilike(f"%{search}%")) | 
            (Product.sku.ilike(f"%{search}%")) |
            (Product.barcode.ilike(f"%{search}%"))
        )
    if category_id:
        query = query.filter(Product.category_id == category_id)

    products = query.all()
    result = []
    for p in products:
        p_out = ProductOut.model_validate(p)
        p_out.stock_quantity = p.inventory.quantity_on_hand if p.inventory else 0.0
        result.append(p_out)
    return result


@router.get("/{product_id}", response_model=ProductOut)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("Products", "VIEW"))
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    p_out = ProductOut.model_validate(product)
    p_out.stock_quantity = product.inventory.quantity_on_hand if product.inventory else 0.0
    return p_out


@router.post("", response_model=ProductOut)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("Products", "FULL"))
):
    # Check SKU uniqueness
    if db.query(Product).filter(Product.sku == payload.sku).first():
        raise HTTPException(status_code=400, detail="Product with this SKU already exists")

    product_data = payload.model_dump()
    initial_stock = product_data.pop("initial_stock", 0.0)

    product = Product(**product_data)
    db.add(product)
    db.flush()

    # Initialize Inventory record
    inventory = Inventory(
        product_id=product.id,
        quantity_on_hand=initial_stock,
        reorder_level=product.min_stock_alert
    )
    db.add(inventory)

    if initial_stock > 0:
        movement = StockMovement(
            product_id=product.id,
            movement_type="INITIAL_STOCK",
            quantity=initial_stock,
            reference_number="INITIAL-SETUP",
            user_id=user.id,
            notes="Initial stock upon product creation"
        )
        db.add(movement)

    db.commit()
    db.refresh(product)

    p_out = ProductOut.model_validate(product)
    p_out.stock_quantity = initial_stock
    return p_out


@router.put("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    payload: ProductCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("Products", "FULL"))
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    product_data = payload.model_dump()
    product_data.pop("initial_stock", None)

    for key, value in product_data.items():
        setattr(product, key, value)

    db.commit()
    db.refresh(product)

    p_out = ProductOut.model_validate(product)
    p_out.stock_quantity = product.inventory.quantity_on_hand if product.inventory else 0.0
    return p_out


@router.delete("/{product_id}")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("Products", "FULL"))
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product.is_active = False
    db.commit()
    return {"message": "Product deactivated successfully"}
