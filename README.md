# 基于 fastapi生态 + tortoise-orm 开发的rest风格的测试平台后端
    注：
    1.tortoise-ORM 与 pydantic2.x不适配，pydantic_model_creator方法会报错，使用pydantic1.10.9版本
        详见 https://stackoverflow.com/questions/76648015/fastapi-tortoise-orm-got-keyerror-module-on-pydantic-model-creator

    2.如果是flask版本的老用户，在数据库初始化完毕过后，执行一下 flast_db_to_fastapi.py 这个脚本，把数据迁移到新的数据库下并自动转化成对应的数据结构
## 线上预览：http://139.196.100.202/#/login  账号：tester、密码：123456

## 前端传送门：https://github.com/zhongyehai/test-platform-fastapi-front

## 系统操作手册：[gitee](https://gitee.com/Xiang-Qian-Zou/api-test-api/blob/master/%E6%93%8D%E4%BD%9C%E6%89%8B%E5%86%8C.md) ，[github](https://github.com/zhongyehai/api-test-api/blob/main/%E6%93%8D%E4%BD%9C%E6%89%8B%E5%86%8C.md)

## Python版本：python => 3.11+

### 1.安装依赖包，推荐清华源：
    sudo pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

### 2.创建MySQL数据库
    数据库名自己取，编码选择utf8mb4，对应config.yaml下db配置为当前数据库信息即可
    查看最大连接数 show variables like 'max_connections';
    设置最大连接数 set global max_connections=16384;


### 3.初始化数据库表结构（项目根目录下依次执行下面命令）：

    3.1、第一次初始化数据库
        3.1.1. 初始化数据库配置、生成迁移文件: aerich init -t config.tortoise_orm_conf
        3.1.2. 把模型映射到数据库中: aerich init-db

    3.2、已经初始化过数据库了，改了数据模型，重新映射
        3.2.1. 对比变更、并映射到数据库: aerich migrate
        3.2.2. 把最新版本的数据结构同步到aerich表: aerich upgrade


### 4.初始化权限、角色、管理员一起一些初始化配置（项目根目录下执行，账号：admin，密码：123456）
    执行 sudo python init_data.py run_init

### 5、若要进行UI自动化：

    5.1安装浏览器，详见：https://www.cnblogs.com/zhongyehai/p/16266455.html

    5.2.准备浏览器驱动
        5.2.1、根据要用来做自动化的浏览器的类型下载对应版本的驱动，详见：https://www.selenium.dev/documentation/zh-cn/webdriver/driver_requirements/
        5.2.2、把下载的驱动放到项目外的 browser_drivers 路径下，项目启动时若没有则会自动创建，若项目未启动过，则需手动创建

    5.3.给驱动加权限：chmod +x chromedriver


### 6.生产环境下的一些配置:
    1.把main端口改为8024启动
    2.把job端口改为8025启动
    3.准备好前端包，并在nginx.location / 下指定前端包的路径
    4.直接把项目下的nginx.conf文件替换nginx下的nginx.conf文件
    5.nginx -s reload 重启nginx

### 7.启动测试平台
    本地开发: 
        运行测试平台主服务              main.py
        运行定时任务/运行任务调度服务     job.py
    
    生产环境:
        项目根目录
        1、给shell加执行权限: chmod 755 start.sh kill.sh
        2、启动项目，执行启动shell: ./start.sh
        3、关闭项目，执行启动shell: ./kill.sh
        注：如果shell报错: -bash: ./kill.sh: /bin/bash^M: bad interpreter: No such file or directory
            需在服务器上打开编辑脚本并保存一下

### 修改依赖后创建依赖：sudo pip freeze > requirements.txt
