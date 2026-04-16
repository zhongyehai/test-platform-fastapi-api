from ..base_view import APIRouter
from ...services.system import monitor as monitor_service

monitor_router = APIRouter()

monitor_router.add_get_route("/metrics", monitor_service.metrics, auth=False, summary="返回prometheus监控数据")
