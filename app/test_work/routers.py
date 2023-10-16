from app.baseView import APIRouter

test_work = APIRouter(
    tags=["测试管理"]
)

from .views import env, kym, weekly, bugTrack
