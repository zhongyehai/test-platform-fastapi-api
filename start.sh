#!/bin/bash

nohup python311 /usr/local/python311/bin/gunicorn -c gunicorn_config_main.py main:app &
echo "主应用启动完成"

nohup python311 /usr/local/python311/bin/gunicorn -c gunicorn_config_job.py job:job &
echo "任务调度应用启动完成"
