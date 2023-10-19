import os

from fastapi import Request
from fastapi.responses import FileResponse

from ..routers import test_work
from ..model_factory import KYMModule
from ..forms.kym import KymProjectForm, ChangeKymForm
from ...config.model_factory import Config
from utils.util.file_util import TEMP_FILE_ADDRESS, FileUtil
from utils.make_data.make_xmind import make_xmind


@test_work.login_post("/kym/project/list", summary="kym服务列表")
async def get_kym_project_list(request: Request):
    project_list = await KYMModule.filter().distinct().values("project")
    return request.app.get_success(data=[{"key": project[0], "value": project[0]} for project in project_list])


@test_work.login_post("/kym/download", summary="导出为xmind")
async def download_kym_as_xmind(form: KymProjectForm, request: Request):
    project = await KYMModule.filter(project=form.project).first()
    file_path = os.path.join(TEMP_FILE_ADDRESS, f"{project.project}.xmind")
    FileUtil.delete_file(file_path)
    make_xmind(file_path, project.kym)
    return FileResponse(file_path)


@test_work.login_post("/kym/project", summary="kym添加服务")
async def add_kym_project(form: KymProjectForm, request: Request):
    kym_data = {"nodeData": {"topic": form.project, "root": True, "children": []}}
    kym_data["nodeData"]["children"] = await Config.get_kym()
    await KYMModule.model_create({"project": form.project, "kym": kym_data}, request.state.user)
    return request.app.post_success()


@test_work.login_post("/kym/detail", summary="获取KYM")
async def get_detail_detail(form: KymProjectForm, request: Request):
    kym = await KYMModule.filter(project=form.project).first()
    return request.app.get_success(data=kym)


@test_work.login_post("/kym", summary="修改KYM")
async def change_kym(form: ChangeKymForm, request: Request):
    kym = await KYMModule.filter(project=form.project).first()
    await kym.model_update({"kym": form.kym}, request.state.user)
    return request.app.put_success()
