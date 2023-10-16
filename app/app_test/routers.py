from app.baseView import APIRouter

app_test = APIRouter(
    tags=["APP测试"]
)

from .views import device, project, module, page, element, suite, case, step, task, report
