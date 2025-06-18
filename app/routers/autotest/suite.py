from typing import List

from ...models.autotest.model_factory import ApiCaseSuitePydantic as CaseSuitePydantic
from ...services.autotest import suite as suite_service
from ..base_view import APIRouter

suite_router = APIRouter()

suite_router.add_get_route(
    "/list", suite_service.get_suite_list, response_model=List[CaseSuitePydantic], summary="获取用例集列表")
suite_router.add_get_route("/template/download", suite_service.get_suite_template, summary="下载用例集导入模板")
suite_router.add_post_route("/upload", suite_service.upload_suite, summary="导入用例集")
suite_router.add_put_route("/sort", suite_service.change_suite_sort, summary="修改用例集排序")
suite_router.add_get_route("", suite_service.get_suite_detail, summary="获取用例集详情")
suite_router.add_post_route("", suite_service.add_suite, summary="新增用例集")
suite_router.add_put_route("", suite_service.change_suite, summary="修改用例集")
suite_router.add_delete_route("", suite_service.delete_suite, summary="删除用例集")
