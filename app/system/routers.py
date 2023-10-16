from app.baseView import APIRouter

system_router = APIRouter(
    tags=["系统管理"]
)

from .views import permission, role, user, error_record, job
