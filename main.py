from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html

from app.baseView import FastAPI
from app.hooks.error_hook import register_exception_handler
from app.hooks.request_hook import register_request_hook
from app.hooks.app_hook import register_app_hook
from config import main_server_port

app = FastAPI(
    docs_url=None,
    redoc_url=None,
    title="测试平台",
    version="1.0.0"
)
app.title = "主程序服务"
app.mount('/static', StaticFiles(directory='static'))

# 注册钩子函数
register_app_hook(app)
register_request_hook(app)
register_exception_handler(app)


# 解决swagger加载慢的问题, 主动注册swagger相关的接口，并返回相关内容
@app.get("/docs", include_in_schema=False)
async def get_swagger_ui():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        swagger_js_url="static/swagger_ui/swagger_ui_bundle.js",
        swagger_css_url="static/swagger_ui/swagger_ui.css",
        swagger_favicon_url="static/swagger_ui/favicon.ico",
    )


@app.get("/redoc", include_in_schema=False)
async def get_redoc():
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=app.title + " - ReDoc",
        redoc_js_url="static/swagger_ui/redoc_standalone.js",
        redoc_favicon_url="static/swagger_ui/favicon.ico"
    )


if __name__ == '__main__':
    import uvicorn

    uvicorn.run('main:app', host="0.0.0.0", port=main_server_port, workers=2)
