from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.models import User, Permission, RolePermission, Role
from app.schemas.schemas import LoginRequest, Token, UserOut, UserRegisterPublic, RoleOut
from app.core.security import verify_password, create_access_token, get_password_hash
from app.core.permissions import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.get("/roles", response_model=List[RoleOut])
def get_public_roles(db: Session = Depends(get_db)):
    """Public endpoint to fetch roles for the registration form."""
    roles = db.query(Role).all()
    res = []
    for r in roles:
        role_perms = [rp.permission for rp in r.permissions]
        r_out = RoleOut(
            id=r.id,
            name=r.name,
            description=r.description,
            permissions=role_perms
        )
        res.append(r_out)
    return res

@router.post("/register", response_model=UserOut)
def register_public_user(payload: UserRegisterPublic, db: Session = Depends(get_db)):
    if payload.password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
    # Check for existing email or username
    if db.query(User).filter((User.email == payload.email) | (User.username == payload.username)).first():
        raise HTTPException(status_code=400, detail="User with this email or username already exists")
    
    role = db.query(Role).filter(Role.id == payload.role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
        
    new_user = User(
        name=payload.name,      
        username=payload.username,
        email=payload.email,
        phone_no=payload.phone_no,
        address=payload.address,
        gender=payload.gender,
        password_hash=get_password_hash(payload.password),
        role_id=payload.role_id,
        is_active=False  # Requires admin approval
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    u_out = UserOut.model_validate(new_user)
    u_out.role_name = role.name
    return u_out

@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated or pending approval"
        )

    # Fetch permissions list for user role
    role_perms = (
        db.query(Permission)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .filter(RolePermission.role_id == user.role_id)
        .all()
    )

    perm_list = [f"{p.module}:{p.action}" for p in role_perms]

    access_token = create_access_token(subject=user.id) 
    user_out = UserOut(
        id=user.id,
        name=user.name,
        username=user.username,
        email=user.email,
        phone_no=user.phone_no,
        address=user.address,
        gender=user.gender,
        role_id=user.role_id,
        role_name=user.role.name if user.role else "User",
        is_active=user.is_active,
        created_at=user.created_at
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_out,
        "permissions": perm_list
    }

@router.get("/me")
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    role_perms = (
        db.query(Permission)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .filter(RolePermission.role_id == current_user.role_id)
        .all()
    )
    perm_list = [f"{p.module}:{p.action}" for p in role_perms]

    return {
        "user": UserOut(
            id=current_user.id,
            name=current_user.name,
            username=current_user.username,
            email=current_user.email,
            phone_no=current_user.phone_no,
            address=current_user.address,
            gender=current_user.gender,
            role_id=current_user.role_id,
            role_name=current_user.role.name if current_user.role else "User",
            is_active=current_user.is_active,
            created_at=current_user.created_at
        ),
        "permissions": perm_list
    }
