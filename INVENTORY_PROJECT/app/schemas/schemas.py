from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field

# ---------------------------------------------------------
# Token & Auth Schemas
# ---------------------------------------------------------
class Token(BaseModel):
    access_token: str
    token_type: str
    user: "UserOut"

class TokenData(BaseModel):
    user_id: Optional[int] = None

class LoginRequest(BaseModel):
    email: str
    password: str

# ---------------------------------------------------------
# RBAC Schemas
# ---------------------------------------------------------
class PermissionOut(BaseModel):
    id: int
    module: str
    action: str
    description: Optional[str] = None

    class Config:
        from_attributes = True

class RoleOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    permissions: List[PermissionOut] = []

    class Config:
        from_attributes = True

class UserCreate(BaseModel):
        name: str
        email: EmailStr
        password: str
        role_id: int

class UserRegisterPublic(BaseModel):
    name: str
    username: str
    email: EmailStr
    password: str
    confirm_password: str
    phone_no: str
    address: str
    gender: str
    role_id: int

class UserOut(BaseModel):
    id: int
    name: str
    username: Optional[str] = None
    email: str
    phone_no: Optional[str] = None
    address: Optional[str] = None
    gender: Optional[str] = None
    role_id: int
    role_name: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# ---------------------------------------------------------
# Master Data Schemas
# ---------------------------------------------------------
class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None

class CategoryOut(CategoryCreate):
    id: int
    is_active: bool

    class Config:
        from_attributes = True

class BrandCreate(BaseModel):
    name: str

class BrandOut(BrandCreate):
    id: int
    is_active: bool

    class Config:
        from_attributes = True

class UnitCreate(BaseModel):
    name: str
    short_name: str

class UnitOut(UnitCreate):
    id: int
    is_active: bool

    class Config:
        from_attributes = True

class ProductCreate(BaseModel):
    sku: str
    barcode: Optional[str] = None
    name: str
    description: Optional[str] = None
    category_id: Optional[int] = None
    brand_id: Optional[int] = None
    unit_id: Optional[int] = None
    cost_price: float = 0.0
    discount_percent: float = 0.0
    selling_price: float = 0.0
    min_stock_alert: int = 0
    image_url: Optional[str] = None
    initial_stock: float = 0.0

class ProductOut(BaseModel):
    id: int
    sku: str
    barcode: Optional[str] = None
    name: str
    description: Optional[str] = None
    category_id: Optional[int] = None
    brand_id: Optional[int] = None
    unit_id: Optional[int] = None
    cost_price: float
    discount_percent: float = 0.0
    selling_price: float
    min_stock_alert: int
    image_url: Optional[str] = None
    is_active: bool
    stock_quantity: float = 0.0

    class Config:
        from_attributes = True

# ---------------------------------------------------------
# Supplier & Customer Schemas
# ---------------------------------------------------------
class SupplierCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None

class SupplierOut(SupplierCreate):
    id: int
    current_balance: float
    is_active: bool

    class Config:
        from_attributes = True

class CustomerCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None

class CustomerOut(CustomerCreate):
    id: int
    current_balance: float
    is_active: bool

    class Config:
        from_attributes = True

# ---------------------------------------------------------
# Inventory Schemas
# ---------------------------------------------------------
class StockAdjustmentCreate(BaseModel):
    product_id: int
    adjustment_type: str  # IN or OUT
    quantity: float
    reason: str

class StockMovementOut(BaseModel):
    id: int
    product_id: int
    product_name: Optional[str] = None
    movement_type: str
    quantity: float
    reference_number: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# ---------------------------------------------------------
# Purchase Schemas
# ---------------------------------------------------------
class PurchaseItemCreate(BaseModel):
    product_id: int
    unit_cost: float
    quantity: float

class PurchaseCreate(BaseModel):
    supplier_id: int
    paid_amount: float = 0.0
    items: List[PurchaseItemCreate]

class PurchaseOut(BaseModel):
    id: int
    purchase_no: str
    supplier_id: int
    supplier_name: Optional[str] = None
    total_amount: float
    paid_amount: float
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

# ---------------------------------------------------------
# Sales Schemas
# ---------------------------------------------------------
class SaleItemCreate(BaseModel):
    product_id: int
    unit_price: float
    quantity: float

class SaleCreate(BaseModel):
    customer_id: Optional[int] = None
    discount_amount: float = 0.0
    tax_amount: float = 0.0
    paid_amount: float = 0.0
    items: List[SaleItemCreate]

class SaleOut(BaseModel):
    id: int
    invoice_no: str
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    salesman_id: int
    salesman_name: Optional[str] = None
    total_amount: float
    discount_amount: float
    tax_amount: float
    final_amount: float
    paid_amount: float
    payment_status: str
    created_at: datetime

    class Config:
        from_attributes = True

# ---------------------------------------------------------
# Payment Schemas
# ---------------------------------------------------------
class PaymentCreate(BaseModel):
    entity_type: str  # CUSTOMER or SUPPLIER
    entity_id: int
    reference_no: Optional[str] = None
    amount: float
    payment_method: str = "CASH"
    notes: Optional[str] = None

class PaymentOut(BaseModel):
    id: int
    payment_no: str
    entity_type: str
    entity_id: int
    amount: float
    payment_method: str
    payment_date: datetime
    reference_no: Optional[str] = None

    class Config:
        from_attributes = True

# ---------------------------------------------------------
# Dashboard & Analytics Summary Schema
# ---------------------------------------------------------
class DashboardSummary(BaseModel):
    total_products: int
    total_stock: float
    low_stock_count: int
    out_of_stock_count: int
    todays_sales: float
    todays_purchases: float
    pending_payments: float
    total_customers: int
    total_suppliers: int
    sales_profit: float
    customer_receivables: float
    supplier_payables: float
