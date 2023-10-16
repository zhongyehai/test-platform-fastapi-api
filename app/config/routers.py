from app.baseView import APIRouter

config_router = APIRouter(
    tags=["配置管理"]
)

from .views import config, business, runEnv, config_type
