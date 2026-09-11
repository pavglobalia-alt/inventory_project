from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.models import User, Role, RolePermission, Permission
from app.schemas.schemas import UserCreate, UserOut, RoleOut
from app.core.security import get_password_hash
from app.core.permissions import require_permission

router = APIRouter(prefix="/users", tags=["User & RBAC Management"])

@router.get("", response_model=List[UserOut])
def list_users(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("Users", "FULL"))
):
    users = db.query(User).all()
    res = []
    for u in users:
        u_out = UserOut.model_validate(u)
        u_out.role_name = u.role.name if u.role else "N/A"
        res.append(u_out)
    return res


@router.post("", response_model=UserOut)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("Users", "FULL"))
):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="User with this email already exists")

    role = db.query(Role).filter(Role.id == payload.role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    new_user = User(
        name=payload.name,
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        role_id=payload.role_id,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    u_out = UserOut.model_validate(new_user)
    u_out.role_name = role.name
    return u_out


@router.get("/roles", response_model=List[RoleOut])
def list_roles(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("Users", "FULL"))
):
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


@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserCreate,
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("Users", "FULL"))
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if new email conflicts with another user
    existing = db.query(User).filter(User.email == payload.email, User.id != user_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email is already in use by another user")

    role = db.query(Role).filter(Role.id == payload.role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    target.name = payload.name
    target.email = payload.email
    target.role_id = payload.role_id
    # Only update password if a real password is provided (not the placeholder)
    if payload.password and payload.password != 'placeholder' and len(payload.password) >= 6:
        from app.core.security import get_password_hash
        target.password_hash = get_password_hash(payload.password)

    db.commit()
    db.refresh(target)

    u_out = UserOut.model_validate(target)
    u_out.role_name = role.name
    return u_out

@router.patch("/{user_id}/status", response_model=UserOut)
def update_user_status(
    user_id: int,
    is_active: bool,
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("Users", "FULL"))
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    target.is_active = is_active
    db.commit()
    db.refresh(target)

    u_out = UserOut.model_validate(target)
    u_out.role_name = target.role.name if target.role else "N/A"
    return u_out
