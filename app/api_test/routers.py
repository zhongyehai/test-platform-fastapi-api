from app.baseView import APIRouter

api_test = APIRouter(
    tags=["接口测试"]
)

from .views import project, module, api, suite, case, step, task, report, stat
