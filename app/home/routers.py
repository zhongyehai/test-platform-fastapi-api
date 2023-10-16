from app.baseView import APIRouter

home = APIRouter(
    tags=["首页"]
)

from .views import apiTest
