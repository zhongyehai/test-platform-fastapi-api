from app.baseView import APIRouter

ui_test = APIRouter(
    tags=["ui测试"]
)

from .views import project, module, page, element, suite, case, step, task, report
