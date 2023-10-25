import multiprocessing

from config import main_server_port

workers = multiprocessing.cpu_count() * 3 + 1 if multiprocessing.cpu_count() * 3 + 1 > 5 else 5  # 至少启动5个worker
threads = 20  # 指定每个worker的线程数，对于fastapi项目没用
bind = f'0.0.0.0:{main_server_port}'  # 访问地址
worker_class = 'uvicorn.workers.UvicornWorker'  # 工作模式协程
worker_connections = 2000  # 每个worker的最大并发量，仅支持 worker 类型为 gthread、eventlet 和 gevent
