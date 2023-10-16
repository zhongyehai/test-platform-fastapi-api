import os
import time

from fastapi import Request, UploadFile, File, Form
from fastapi.responses import FileResponse

from ..routers import assist_router
from ..forms.file import GetFileListForm, CheckFileIsExistsForm

from utils.util.file_util import CASE_FILE_ADDRESS, CALL_BACK_ADDRESS, TEMP_FILE_ADDRESS, \
    UI_CASE_FILE_ADDRESS, BROWSER_DRIVER_ADDRESS, FileUtil

folders = {
    "case": CASE_FILE_ADDRESS,
    "ui_case": UI_CASE_FILE_ADDRESS,
    "callBack": CALL_BACK_ADDRESS,
    "temp": TEMP_FILE_ADDRESS,
    "driver": BROWSER_DRIVER_ADDRESS,
}


def format_time(atime):
    """ 时间戳转年月日时分秒 """
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(atime))


def make_pagination(data_list, pag_size, page_num):
    """ 数据列表分页 """
    start = (page_num - 1) * pag_size
    end = start + pag_size
    return data_list[start: end]


@assist_router.login_post("/file/list", summary="获取文件列表")
async def get_file_list(form: GetFileListForm, request: Request):
    addr = folders.get(form.file_type, "case")
    file_list = os.listdir(addr)
    filter_list = make_pagination(file_list, form.page_size, form.page_num)

    parsed_file_list = []
    for file_name in filter_list:
        file_info = os.stat(os.path.join(addr, file_name))
        parsed_file_list.append({
            "name": file_name,  # 文件名
            "size": file_info.st_size,  # 文件文件大小
            "lastVisitTime": format_time(file_info.st_atime),  # 最近一次使用时间
            "LastModifiedTime": format_time(file_info.st_mtime),  # 最后一次更新时间
        })
    return request.app.success("获取成功", data={"data": parsed_file_list, "total": file_list.__len__()})


@assist_router.login_post("/file/check", summary="检查文件是否已存在")
async def check_file_is_exists(form: CheckFileIsExistsForm, request: Request):
    is_exists = os.path.exists(os.path.join(folders.get(form.file_type, "case"), form.file_name))
    return request.app.fail("文件已存在") if is_exists else request.app.success("文件不存在")


@assist_router.login_post("/file/download", summary="下载文件")
async def download_file(form: CheckFileIsExistsForm, request: Request):
    is_exists = os.path.exists(os.path.join(folders.get(form.file_type, "case"), form.file_name))
    if is_exists:
        return FileResponse(os.path.join(folders.get(form.file_type, "case"), form.file_name))
    return request.app.fail("文件不存在")


@assist_router.login_post("/file/upload", summary="文件上传")
async def upload_file(request: Request, file: UploadFile = File(), file_type: str = Form()):
    file_content = await file.read()
    with open(os.path.join(folders.get(file_type, "case"), file.filename), 'wb') as f:
        f.write(file_content)
    return request.app.success(msg="上传成功", data=file.filename)


@assist_router.login_delete("/file", summary="删除文件")
async def delete_file(form: CheckFileIsExistsForm, request: Request):
    path = os.path.join(folders.get(form.file_type, "case"), form.file_name)
    FileUtil.delete_file(path)
    return request.app.success("删除成功", data={"name": form.file_name})
