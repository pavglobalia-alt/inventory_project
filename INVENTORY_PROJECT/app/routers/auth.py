from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.models import User, Permission, RolePermission
from app.schemas.schemas import LoginRequest, Token, UserOut
from app.core.security import verify_password, create_access_token
from app.core.permissions import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

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
            detail="User account is deactivated"
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
        email=user.email,
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
            email=current_user.email,
            role_id=current_user.role_id,
            role_name=current_user.role.name if current_user.role else "User",
            is_active=current_user.is_active,
            created_at=current_user.created_at
        ),
        "permissions": perm_list
    }
