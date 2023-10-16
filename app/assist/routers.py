from app.baseView import APIRouter

assist_router = APIRouter(
    tags=["自动化测试辅助"]
)

from .views import script, call_back, error_record, data_pool, hits, swagger, file
