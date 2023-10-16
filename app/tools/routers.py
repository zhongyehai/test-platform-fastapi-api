from app.baseView import APIRouter

tool = APIRouter(
    tags=["工具"]
)

from .views import examination, make_user, mock_data
