import multiprocessing

from config import main_server_port

# 跑测试的时候会阻塞线程，所以多起几个worker
workers = multiprocessing.cpu_count() * 3 + 1 if multiprocessing.cpu_count() * 3 + 1 > 5 else 5
bind = f'0.0.0.0:{main_server_port}'  # 访问地址
worker_class = 'uvicorn.workers.UvicornWorker'  # 工作模式协程
