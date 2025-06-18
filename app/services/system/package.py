import subprocess

from fastapi import Request

from ...schemas.system import package as schema
from ...models.config.model_factory import Config


async def get_package_list(request: Request):
    """ 获取pip包列表 """
    pip_command = await Config.get_pip_command()
    result = subprocess.run([pip_command, 'list'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return request.app.get_success(result.stdout)


async def install_package(request: Request, form: schema.PackageInstallForm):
    """ pip安装包 """
    package = f'{form.name.strip()}=={form.version.strip()}' if form.version else form.name
    pip_command = await Config.get_pip_command()
    result = subprocess.run([pip_command, 'install', package], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode == 0:
        return request.app.success(msg="安装成功")
    return request.app.fail(msg=f"安装失败：{result.stderr}")
