from tortoise import Tortoise
from tortoise.contrib.fastapi import register_tortoise

import config
from utils.logs.log import logger
from utils.message.send_report import send_server_status

def register_app_hook(app):
    @app.on_event("startup")
    async def startup_event():
        """ 应用启动事件 """

        app.conf, app.logger = config, logger

        # 注册orm
        register_tortoise(
            app,
            config=config.tortoise_orm_conf,
            add_exception_handlers=True
        )

        # 注册蓝图
        from app.routers.autotest import api_test, app_test, ui_test
        from app.routers.system import system_router
        from app.routers.assist import assist_router
        from app.routers.manage import manage_router
        from app.routers.tools import tools_router
        from app.routers.config import config_router
        app.include_router(api_test, prefix='/api/api-test', tags=["接口自动化测试"])
        app.include_router(app_test, prefix='/api/app-test', tags=["app自动化测试"])
        app.include_router(ui_test, prefix='/api/ui-test', tags=["ui自动化测试"])
        app.include_router(system_router, prefix='/api/system', tags=["系统管理"])
        app.include_router(assist_router, prefix='/api/assist', tags=["自动化测试辅助"])
        app.include_router(manage_router, prefix='/api/manage', tags=["测试管理"])
        app.include_router(tools_router, prefix='/api/tools', tags=["工具"])
        app.include_router(config_router, prefix='/api/config', tags=["配置管理"])

        app.logger.info(f'\n\n\n{"*" * 20} 服务【{app.title}】启动完成 {"*" * 20}\n\n\n'"")
        if config.is_linux:
            await send_server_status(config.AuthInfo.SECRET_KEY, app.title, action_type='启动')

    @app.on_event("shutdown")
    async def shutdown_event():
        await Tortoise.close_connections()
        app.logger.info(f'\n\n\n{"*" * 20} 服务【{app.title}】关闭完成 {"*" * 20}\n\n\n'"")
        if config.is_linux:
            await send_server_status(config.AuthInfo.SECRET_KEY, app.title, action_type='关闭')
