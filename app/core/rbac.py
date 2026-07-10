from fastapi import HTTPException, status

from app.models.user import UserRole


# Role hierarchy — higher index = more privilege
ROLE_HIERARCHY = [
    UserRole.viewer,
    UserRole.sales_agent,
    UserRole.sales_manager,
    UserRole.admin,
]


def has_role(user_role: UserRole, required_role: UserRole) -> bool:
    """Return True if user_role is >= required_role in hierarchy."""
    try:
        return ROLE_HIERARCHY.index(user_role) >= ROLE_HIERARCHY.index(required_role)
    except ValueError:
        return False


def require_roles(*allowed_roles: UserRole):
    """
    Returns a FastAPI dependency that raises 403 if the current user's
    role is not in the allowed_roles list.

    Usage:
        @router.get("/admin-only", dependencies=[Depends(require_roles(UserRole.admin))])
    """
    from fastapi import Depends
    from app.api.deps import get_current_active_user
    from app.models.user import User

    def _check(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )
        return current_user

    return Depends(_check)


def can_manage_lead(
    actor_role: UserRole,
    actor_id: str,
    lead_created_by_id: str,
    lead_assigned_to_id: str | None = None,
) -> bool:
    """
    Admin/Sales Manager can manage any lead.
    Sales Agent can manage leads they created or are assigned to.
    Viewer cannot manage leads.
    """
    if actor_role in (UserRole.admin, UserRole.sales_manager):
        return True
    if actor_role == UserRole.sales_agent and (
        actor_id == lead_created_by_id or actor_id == lead_assigned_to_id
    ):
        return True
    return False


def can_use_attendance(role: UserRole) -> bool:
    return role != UserRole.viewer


def can_manage_attendance_admin(role: UserRole) -> bool:
    return role == UserRole.admin


def can_approve_leave(
    actor_role: UserRole,
    actor_id: str,
    applicant_manager_id: str | None,
) -> bool:
    if actor_role == UserRole.admin:
        return True
    if actor_role == UserRole.sales_manager and applicant_manager_id == actor_id:
        return True
    return False
