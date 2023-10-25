import datetime
import json
import hashlib
import threading
from contextlib import contextmanager

import pymysql

from config import default_web_hook

hash_secret_key = ''  # 密码加密字符串，与config.hash_secret_key 一致，否则会导致加密出来的字符串不一致

from_db, to_db = '', ''  # 数据库名

from_db_info = {
    "host": "",
    "user": "",
    "password": "",
    "port": 3306,
    "charset": "utf8",
}

to_db_info = from_db_info  # 数据库链接信息


def format_datetime(data, fields=[]):
    for field in fields:
        if field in data:
            try:
                data[field] = data[field].strftime("%Y-%m-%d %H:%M:%S")
            except:
                pass
    return data


def format_step_data(step_data):
    try:
        new_data = json.loads(step_data)
        if new_data.get("request", {}).get("body"): new_data["request"].pop("body")
        new_data.pop("before")
        new_data.pop("after")
        return json.dumps(new_data, ensure_ascii=False)
    except:
        return step_data


def format_temp_variables(temp_variables):
    if not temp_variables or temp_variables == 'null':
        return '{}'
    return temp_variables


def format_report_summary(summary):
    """
    summary:
    {
        "stat": {
            "testcases": {
                "fail": 1,
                "total": 1,
                "project": "贷前巡检",
                "success": 0
            },
            "teststeps": {
                "total": 14,
                "errors": 0,
                "skipped": 1,
                "failures": 1,
                "successes": 12,
                "expectedFailures": 0,
                "unexpectedSuccesses": 0
            }
        },
        "time": {
            "duration": 4.6989,
            "start_at": "2023-07-04 09:30:01",
            "start_date": "2023-07-04 09:30:01"
        },
        "run_env": "us_test",
        "success": false,
        "env_name": "开发-美国",
        "is_async": null,
        "run_type": "api",
        "count_api": 14,
        "count_step": 14,
        "count_element": 0
    }
    """
    new_summary = {
        "result": "success" if summary.get("success") else "fail",
        "env": {
            "code": summary.get("run_env"),
            "name": summary.get("env_name")
        },
        "stat": {
            "count": {
                "api": summary.get("count_api", 0),
                "step": summary.get("count_step", 0),
                "element": summary.get("count_element", 0)
            },
            "test_case": {
                "fail": summary.get("stat", {}).get("testcases", {}).get("fail", 0),
                "total": summary.get("stat", {}).get("testcases", {}).get("total", 0),
                "success": summary.get("stat", {}).get("testcases", {}).get("success", 0),
                "skip": 0,
                "error": 0
            },
            "test_step": {
                "fail": summary.get("stat", {}).get("teststeps", {}).get("failures", 0),
                "skip": summary.get("stat", {}).get("teststeps", {}).get("skipped", 0),
                "error": summary.get("stat", {}).get("teststeps", {}).get("errors", 0),
                "total": summary.get("stat", {}).get("teststeps", {}).get("total", 0),
                "success": summary.get("stat", {}).get("teststeps", {}).get("successes", 0)
            }
        },
        "time": {
            "end_at": summary.get("end_at", ""),
            "start_at": summary.get("start_at") or summary.get("start_date"),
            "all_duration": summary.get("duration", 0),
            "case_duration": summary.get("duration", 0),
            "step_duration": summary.get("duration", 0)
        }
    }
    return json.dumps(new_summary)


def format_report_case_summary(summary):
    """
    summary:
    {
        "success": false,
        "case_id": 823,
        "project_id": 152,
        "stat": {
            "total": 14,
            "failures": 1,
            "errors": 0,
            "skipped": 1,
            "expectedFailures": 0,
            "unexpectedSuccesses": 0,
            "successes": 12
        },
        "time": {
            "start_at": 1688434201.5395257,
            "start_date": "2023-07-04 09:30:01",
            "duration": 4.6989
        },
        "name": "xx流程"
    }
    """
    new_summary = {
        "result": "success" if summary.get("success") else "fail",
        "stat": {
            "fail": summary.get("stat", {}).get("failures", 0),
            "total": summary.get("stat", {}).get("total", 0),
            "success": summary.get("stat", {}).get("successes", 0),
            "skip": summary.get("stat", {}).get("skipped", 0),
            "error": summary.get("stat", {}).get("errors", 0)
        },
        "time": {
            "end_at": summary.get("end_at", ""),
            "start_at": summary.get("start_at") or summary.get("start_date"),
            "all_duration": summary.get("duration", 0),
            "case_duration": summary.get("duration", 0),
            "step_duration": summary.get("duration", 0)
        }
    }
    return json.dumps(new_summary)


def format_report_step_summary(summary):
    """
    summary:
    {
        "response_time_ms": 135.97,
        "elapsed_ms": 134.898,
        "content_size": 32,
        "request_at": "2023-07-04 09:30:01",
        "response_at": "2023-07-04 09:30:01"
    }
    """
    new_summary = {
        "elapsed_ms": summary.get("elapsed_ms"),
        "request_at": summary.get("request_at"),
        "response_at": summary.get("response_at"),
        "content_size": summary.get("content_size")
    }
    return json.dumps(new_summary)


def get_now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def password_to_hash(password):
    """ h密码转hash值 """
    password_and_secret_key = password + hash_secret_key
    hash_obj = hashlib.md5(password_and_secret_key.encode('utf-8'))  # 使用md5函数进行加密
    return hash_obj.hexdigest()  # 转换为16进制


def send_msg(res_data):
    """ 迁移完毕后，发送报告 """
    all_duration, all_count = 0, 0
    text = f'### 数据迁移通知 {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} \n> '
    for table_name, table_stat in res_data.items():
        total_seconds = round((table_stat["end_at"] - table_stat["start_at"]).total_seconds(), 4)
        all_duration += total_seconds
        all_count += table_stat["count"]
        text += (f'\n'
                 f'#### 表名: <font color=#409EFF>{table_name} </font>\n> '
                 f'#### 开始时间: {table_stat["start_at"].strftime("%Y-%m-%d %H:%M:%S")} \n> '
                 f'#### 结束时间: {table_stat["end_at"].strftime("%Y-%m-%d %H:%M:%S")} \n> '
                 f'#### 耗时: <font color=#FF0000>{total_seconds} </font>秒\n> '
                 f'#### 共迁移: <font color=#FF0000>{table_stat["count"]} </font>条数据 \n> '
                 )
    text += (
        f'\n'
        f'#### 总共耗时: <font color=#FF0000>{all_duration} </font>秒\n> '
        f'#### 总共迁移: <font color=#FF0000>{all_count} </font>条数据\n> '
    )
    print(text)
    import requests
    requests.post(
        url='https://oapi.dingtalk.com/robot/send?access_token=986c4f98c66b777b6d628e8efe10cc5b4875e87086bcf2d43387cafac2d34a04',
        json={
            "msgtype": "markdown",
            "markdown": {
                "title": "数据迁移进度通知",
                "text": text
            }
        }
    )


class DbOption:
    """ 数据库操作 """

    def __init__(self, db_info):
        self.db_info = db_info

    @contextmanager
    def connect_db(self):
        """ 每次执行前连接 """
        connect = pymysql.connect(**self.db_info)
        cursor = connect.cursor(cursor=pymysql.cursors.DictCursor)
        try:
            yield cursor
            connect.commit()
        except:  # 提交异常时需要回滚事件
            connect.rollback()
        finally:  # 关闭连接
            cursor.close()
            connect.close()

    def execute(self, sql):
        """ 执行SQL语句 """
        print(f'db.execute.sql: {sql}')
        with self.connect_db() as db:
            db.execute(sql)

    def fetchone(self, sql):
        """ 查询一条数据 """
        data = None
        with self.connect_db() as db:
            print(f'db.fetchone.sql: {sql}')
            db.execute(sql)
            data = db.fetchone()
            print(f'db.fetchone.res: {data}')

            if data:
                data = format_datetime(data, ["created_time", "update_time"])

        return data

    def fetchall(self, sql):
        """ 查询所有数据 """
        data_list = None
        with self.connect_db() as db:
            print(f'db.fetchall.sql: {sql}')
            db.execute(sql)
            data = db.fetchall()
            print(f'db.fetchall.res: {data}')

            data_list = [format_datetime(d, ["created_time", "update_time"]) for d in data]
        return data_list


from_connect, to_connect = DbOption(from_db_info), DbOption(to_db_info)


def migration_system():
    def migration_system_permission():
        tabel_name = 'system_permission'
        count, start_at = 0, datetime.datetime.now()
        print(f'开始执行【{tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{tabel_name} (
                        id, create_time, update_time, create_user, update_user, name, `desc`, num, source_addr, source_type, source_class
                    )  values {(
                        data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                        data["name"], data["desc"] or '', -1 if data["num"] is None else data["num"], data["source_addr"], data["source_type"], data["source_class"]
                    )} """)
                    db_data = to_connect.fetchone(f""" select * from {to_db}.{tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1
        to_connect.execute(f""" update {to_db}.{tabel_name} set `num`=null where `num`=-1 """)
        to_connect.execute(f""" update {to_db}.{tabel_name} set `desc`=null where `desc`='' """)
        print(f'【{tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    def migration_system_role():
        tabel_name = 'system_role'
        count, start_at = 0, datetime.datetime.now()
        print(f'开始执行【{tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{tabel_name} (
                        id, create_time, update_time, create_user, update_user, name, `desc`, extend_role
                    )  values {(
                        data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                        data["name"], data["desc"] or '', data["extend_role"]
                    )} """)
                    db_data = to_connect.fetchone(f""" select * from {to_db}.{tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1
        to_connect.execute(f""" update {to_db}.{tabel_name} set `desc`=null where `desc`='' """)
        print(f'【{tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    def migration_system_role_permissions():
        tabel_name = 'system_role_permissions'
        count, start_at = 0, datetime.datetime.now()
        print(f'开始执行【{tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{tabel_name} (
                        id, create_time, update_time, create_user, update_user, role_id, permission_id
                    )  values {(
                        data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                        data["role_id"], data["permission_id"]
                    )} """)
                    db_data = to_connect.fetchone(f""" select * from {to_db}.{tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1

        print(f'【{tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    def migration_system_user():
        tabel_name = 'system_user'
        count, start_at = 0, datetime.datetime.now()
        print(f'开始执行用户数据迁移')
        to_connect.execute(f""" truncate {to_db}.{tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.system_user 
                    (id, create_time, update_time, create_user, update_user, account, password, name, status, 
                    business_list, need_change_password) 
                    values {
                    (data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                     data["account"], password_to_hash(data["account"]), data["name"], "enable" if data["status"] == 1 else "disable",
                     data["business_list"], 1)
                    } """)
                    db_data = to_connect.fetchone(f""" select * from {to_db}.{tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1
        print(f'用户数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    def migration_system_user_roles():
        tabel_name = 'system_user_roles'
        count, start_at = 0, datetime.datetime.now()
        print(f'开始执行【{tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{tabel_name} (
                        id, create_time, update_time, create_user, update_user, role_id, user_id
                    )  values {(
                        data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                        data["role_id"], data["user_id"]
                    )} """)
                    db_data = to_connect.fetchone(f""" select * from {to_db}.{tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1
        print(f'【{tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    def migration_system_error_record():
        tabel_name = 'system_error_record'
        count, start_at = 0, datetime.datetime.now()
        print(f'开始执行【{tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{tabel_name} (
                        id, create_time, update_time, create_user, update_user,
                        ip, url, method, headers, params, data_form, data_json, detail
                    )  values {(
                        data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                        data["ip"] or '', data["url"], data["method"], data["headers"], data["params"], data["data_form"],
                        data["data_json"], data["detail"]
                    )} """)

                    db_data = to_connect.fetchone(f""" select * from {to_db}.{tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1

        to_connect.execute(f""" update {to_db}.{tabel_name} set `ip`=null where `ip`='' """)
        print(f'【{tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    send_msg({
        "system_permission": migration_system_permission(),
        "system_role": migration_system_role(),
        "system_role_permissions": migration_system_role_permissions(),
        "system_user": migration_system_user(),
        "system_user_roles": migration_system_user_roles(),
        "system_error_record": migration_system_error_record()
    })


def migration_config():
    def migration_config_type():
        tabel_name = 'config_type'
        count, start_at = 0, datetime.datetime.now()
        print(f'开始执行【{tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{tabel_name} (
                        id, create_time, update_time, create_user, update_user, name, `desc`
                    )  values {(
                        data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                        data["name"], data["desc"] or ''
                    )} """)
                    db_data = to_connect.fetchone(f""" select * from {to_db}.{tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1
        to_connect.execute(f""" update {to_db}.{tabel_name} set `desc`=null where `desc`='' """)
        print(f'【{tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    def migration_config_config():
        tabel_name = 'config_config'
        count, start_at = 0, datetime.datetime.now()
        print(f'开始执行【{tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{tabel_name} (
                        id, create_time, update_time, create_user, update_user, name, `desc`, value, type
                    )  values {(
                        data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                        data["name"], data["desc"] or '', data["value"], data["type"]
                    )} """)
                    db_data = to_connect.fetchone(f""" select * from {to_db}.{tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1
        to_connect.execute(f""" update {to_db}.{tabel_name} set `desc`=null where `desc`='' """)
        print(f'【{tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    def migration_config_business():
        tabel_name = 'config_business'
        count, start_at = 0, datetime.datetime.now()
        print(f'开始执行【{tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{tabel_name} (
                        id, create_time, update_time, create_user, update_user,
                         name, num, `desc`, code, env_list, 
                         receive_type, 
                         webhook_list, bind_env
                    )  values {(
                        data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                        data["name"], -1 if data["num"] is None else data["num"], data["desc"] or '', data["code"], data["env_list"],
                        "not_receive" if data["receive_type"] in ["0", None] else data["receive_type"],
                        data["webhook_list"], data["bind_env"]
                    )} """)
                    db_data = to_connect.fetchone(f""" select * from {to_db}.{tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1
        to_connect.execute(f""" update {to_db}.{tabel_name} set `num`=null where `num`=-1 """)
        to_connect.execute(f""" update {to_db}.{tabel_name} set `desc`=null where `desc`='' """)
        print(f'【{tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    def migration_config_run_env():
        tabel_name = 'config_run_env'
        count, start_at = 0, datetime.datetime.now()
        print(f'开始执行【{tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{tabel_name} (
                        id, create_time, update_time, create_user, update_user, name, num, `desc`, code, `group`
                    )  values {(
                        data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                        data["name"], -1 if data["num"] is None else data["num"], data["desc"] or '', data["code"], data["group"]
                    )} """)
                    db_data = to_connect.fetchone(f""" select * from {to_db}.{tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1
        to_connect.execute(f""" update {to_db}.{tabel_name} set `num`=null where `num`=-1 """)
        to_connect.execute(f""" update {to_db}.{tabel_name} set `desc`=null where `desc`='' """)
        print(f'【{tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    send_msg({
        "config_type": migration_config_type(),
        "config_config": migration_config_config(),
        "config_business": migration_config_business(),
        "config_run_env": migration_config_run_env()
    })


def migration_api_test():
    def migration_project():
        tabel_name = 'api_test_project'
        count, start_at = 0, datetime.datetime.now()
        print(f'开始执行【{tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{tabel_name} (
                        id, create_time, update_time, create_user, update_user, name, manager, script_list, swagger, num, last_pull_status, business_id
                    )  values {(
                        data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                        data["name"], data["manager"], data["script_list"], data["swagger"], -1 if data["num"] is None else data["num"], data["last_pull_status"], data["business_id"]
                    )} """)
                    db_data = to_connect.fetchone(f""" select * from {to_db}.{tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1
        to_connect.execute(f""" update {to_db}.{tabel_name} set num=null where num=-1 """)
        print(f'【{tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    def migration_project_env():
        tabel_name = 'api_test_project_env'
        count, start_at = 0, datetime.datetime.now()
        print(f'开始执行【{tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{tabel_name} (
                        id, create_time, update_time, create_user, update_user, host, variables, env_id, project_id, headers
                    )  values {(
                        data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                        data["host"], data["variables"], data["env_id"], data["project_id"], data["headers"]
                    )} """)
                    db_data = to_connect.fetchone(f""" select * from {to_db}.{tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1
        print(f'【{tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    def migration_module():
        tabel_name = 'api_test_module'
        count, start_at = 0, datetime.datetime.now()
        print(f'开始执行【{tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{tabel_name} (
                        id, create_time, update_time, create_user, update_user, name, num, parent, project_id, controller
                    )  values {(
                        data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                        data["name"], -1 if data["num"] is None else data["num"], data["parent"] or -1, data["project_id"], data["controller"] or ''
                    )} """)
                    db_data = to_connect.fetchone(f""" select * from {to_db}.{tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1
        to_connect.execute(f""" update {to_db}.{tabel_name} set num=null where num=-1 """)
        to_connect.execute(f""" update {to_db}.{tabel_name} set parent=null where parent=-1 """)
        to_connect.execute(f""" update {to_db}.{tabel_name} set controller=null where controller='' """)
        print(f'【{tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    def migration_api():
        tabel_name = 'api_test_api'
        count, start_at = 0, datetime.datetime.now()
        print(f'开始执行【{tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{tabel_name} (
                        id, create_time, update_time, create_user, update_user, 
                        name, num, `desc`, project_id, module_id, time_out,
                        addr, up_func, down_func, method, level, headers,
                        params, body_type, data_form, data_urlencoded, data_json, 
                        data_text, response, extracts, validates, 
                        status, quote_count
                    )  values {(
                        data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                        data["name"], -1 if data["num"] is None else data["num"], data["desc"] or '', data["project_id"], data["module_id"], data["time_out"],
                        data["addr"], data["up_func"] if data["up_func"] else '[]', data["down_func"] if data["down_func"] else '[]', data["method"], data["level"], data["headers"],
                        data["params"], data["data_type"], data["data_form"], data["data_urlencoded"], data["data_json"],
                        data["data_text"] or '', data["response"] or '{}', data["extracts"], data["validates"],
                        "disable" if data["deprecated"] == 1 else "enable", data["quote_count"]
                    )} """)

                    db_data = to_connect.fetchone(f""" select * from {to_db}.{tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1
        to_connect.execute(f""" update {to_db}.{tabel_name} set num=null where num=-1 """)
        to_connect.execute(f""" update {to_db}.{tabel_name} set `desc`=null where `desc`='' """)
        to_connect.execute(f""" update {to_db}.{tabel_name} set `data_text`=null where `data_text`='' """)
        print(f'【{tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    def migration_case_suite():
        tabel_name = 'api_test_case_suite'
        count, start_at = 0, datetime.datetime.now()
        print(f'开始执行【{tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{tabel_name} (
                        id, create_time, update_time, create_user, update_user, name, num, parent, project_id, 
                        suite_type
                    )  values {(
                        data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                        data["name"], -1 if data["num"] is None else data["num"], data["parent"] or -1, data["project_id"],
                        "make_data" if data["suite_type"] == "assist" else data["suite_type"]
                    )} """)
                    db_data = to_connect.fetchone(f""" select * from {to_db}.{tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1
        to_connect.execute(f""" update {to_db}.{tabel_name} set num=null where num=-1 """)
        to_connect.execute(f""" update {to_db}.{tabel_name} set parent=null where parent=-1 """)
        print(f'【{tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    def migration_case():
        tabel_name = 'api_test_case'
        count, start_at = 0, datetime.datetime.now()
        print(f'开始执行【{tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{tabel_name} (
                        id, create_time, update_time, create_user, update_user,
                        name, num, `desc`, status, run_times, script_list, 
                        variables, output, skip_if, suite_id, headers
                    )  values {(
                        data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                        data["name"], -1 if data["num"] is None else data["num"], data["desc"] or '', data["status"], data["run_times"], data["script_list"],
                        data["variables"], data["output"], data["skip_if"], data["suite_id"], data["headers"]
                    )} """)

                    db_data = to_connect.fetchone(f""" select * from {to_db}.{tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1

        to_connect.execute(f""" update {to_db}.{tabel_name} set num=0 where num=-1 """)
        to_connect.execute(f""" update {to_db}.{tabel_name} set `desc`=null where `desc`='' """)

        print(f'【{tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    def migration_step():
        tabel_name = 'api_test_step'
        count, start_at = 0, datetime.datetime.now()
        print(f'开始执行【{tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{tabel_name} (
                        id, create_time, update_time, create_user, update_user, 
                        name, num, case_id, api_id, time_out,
                        up_func, down_func, headers, params, body_type,
                         data_form, data_urlencoded, data_json, data_text, extracts, 
                         validates, data_driver, quote_case, replace_host, skip_if, 
                         status, skip_on_fail, pop_header_filed
                    )  values {(
                        data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                        data["name"], -1 if data["num"] is None else data["num"], data["case_id"], data["api_id"] or -1, data["time_out"],
                        data["up_func"] if data["up_func"] else '[]', data["down_func"] if data["down_func"] else '[]', data["headers"], data["params"], data["data_type"],
                        data["data_form"], data["data_urlencoded"], data["data_json"], data["data_text"] or '', data["extracts"],
                        data["validates"], '[]' if data["data_driver"] in [None, 'null'] else data["data_driver"], data["quote_case"] or -1, data["replace_host"], data["skip_if"],
                        "disable" if data["status"] == 0 else "enable", data["skip_on_fail"],
                        '[]' if data["pop_header_filed"] in [None, '', 'null'] else data["pop_header_filed"]
                    )} """)

                    db_data = to_connect.fetchone(f""" select * from {to_db}.{tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1

        to_connect.execute(f""" update {to_db}.{tabel_name} set api_id=null where api_id=-1 """)
        to_connect.execute(f""" update {to_db}.{tabel_name} set `quote_case`=null where `quote_case`=-1 """)
        to_connect.execute(f""" update {to_db}.{tabel_name} set `data_text`=null where `data_text`='' """)

        print(f'【{tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    def migration_task():
        tabel_name = 'api_test_task'
        count, start_at = 0, datetime.datetime.now()
        print(f'开始执行【{tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{tabel_name} (
                        id, create_time, update_time, create_user, update_user,
                        name, num, env_list, case_ids, task_type, cron, 
                        is_send, 
                        receive_type, webhook_list, email_server, email_from, 
                        email_pwd, email_to, status, is_async, suite_ids, 
                        call_back, project_id, conf, skip_holiday
                    )  values {(
                        data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                        data["name"], -1 if data["num"] is None else data["num"], data["env_list"], data["case_ids"], data["task_type"], data["cron"],
                        "not_send" if data["is_send"] == "1" else "always" if data["is_send"] == "2" else "on_fail",
                        data["receive_type"] or '', data["webhook_list"] or '[]', data["email_server"], data["email_from"],
                        data["email_pwd"], data["email_to"] or '[]', "disable" if data["status"] == 0 else "enable", 0, data["suite_ids"],
                        data["call_back"] or '[]', data["project_id"], '{}' if data["conf"] is None or data["conf"] == 'null' else data["conf"], 1
                    )} """)

                    db_data = to_connect.fetchone(f""" select * from {to_db}.{tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1

        to_connect.execute(f""" update {to_db}.{tabel_name} set conf='{json.dumps({})}' where conf='null' """)
        to_connect.execute(f""" update {to_db}.{tabel_name} set num=0 where num=-1 """)
        to_connect.execute(f""" update {to_db}.{tabel_name} set `receive_type`=null where `receive_type`='' """)

        print(f'【{tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    def migration_report():
        tabel_name = 'api_test_report'
        count, start_at = 0, datetime.datetime.now()
        print(f'开始执行【{tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{tabel_name} (
                        id, create_time, update_time, create_user, update_user,
                        name, status, is_passed, run_type, project_id, 
                        env,  trigger_type, process, retry_count, run_id, 
                        temp_variables, batch_id, summary
                    )  values {(
                        data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                        data["name"], data["status"], data["is_passed"], data["run_type"], data["project_id"],
                        data["env"], data["trigger_type"], data["process"], data["retry_count"], data["run_id"],
                        format_temp_variables(data["temp_variables"]), data["batch_id"], format_report_summary(json.loads(data["summary"]))
                    )} """)

                    db_data = to_connect.fetchone(f""" select * from {to_db}.{tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1
                print(f'{max_id["max(id)"]} => {i}')

        # to_connect.execute(f""" update {to_db}.{tabel_name} set temp_variables='{}' where temp_variables='null' """)
        print(f'【{tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    def migration_report_case():
        tabel_name = 'api_test_report_case'
        count, start_at = 0, datetime.datetime.now()
        print(f'开始执行【{tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{tabel_name} (
                        id, create_time, update_time, create_user, update_user,
                        name, case_id, report_id, result, case_data, 
                        summary,  error_msg
                    )  values {(
                        data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                        data["name"], data["from_id"], data["report_id"], data["result"], data["case_data"],
                        format_report_case_summary(json.loads(data["summary"])), data["error_msg"] or ''
                    )} """)

                    db_data = to_connect.fetchone(f""" select * from {to_db}.{tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1
                print(f'{max_id["max(id)"]} => {i}')
        print(f'【{tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    def migration_report_step():
        tabel_name = 'api_test_report_step'
        count, start_at = 0, datetime.datetime.now()
        print(f'开始执行【{tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{tabel_name} (
                        id, create_time, update_time, create_user, update_user,
                        name, case_id, step_id, report_case_id, report_id, 
                        process, result, step_data, summary, api_id
                    )  values {(
                        data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                        data["name"], data["case_id"] or -1, data["step_id"] or -1, data["report_case_id"], data["report_id"],
                        data["process"], data["result"], format_step_data(data["step_data"]), format_report_step_summary(json.loads(data["summary"])), data["from_id"]
                    )} """)

                    db_data = to_connect.fetchone(f""" select * from {to_db}.{tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1
                print(f'{max_id["max(id)"]} => {i}')
        to_connect.execute(f""" update {to_db}.{tabel_name} set step_id=null where step_id=-1 """)
        to_connect.execute(f""" update {to_db}.{tabel_name} set case_id=null where case_id=-1 """)
        print(f'【{tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    send_msg({
        "api_project": migration_project(),
        "api_project_env": migration_project_env(),
        "api_api": migration_api(),
        "api_case_suite": migration_case_suite(),
        "api_case": migration_case(),
        "api_step": migration_step(),
        "api_task": migration_task(),
        "api_report": migration_report(),
        "api_report_case": migration_report_case(),
        "api_report_step": migration_report_step()
    })


def migration_ui_test():
    def migration_project():
        tabel_name = 'web_ui_test_project'
        count, start_at = 0, datetime.datetime.now()
        print(f'开始执行【{tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{tabel_name} (
                        id, create_time, update_time, create_user, update_user, name, manager, script_list, num, business_id
                    )  values {(
                        data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                        data["name"], data["manager"], data["script_list"], -1 if data["num"] is None else data["num"], data["business_id"]
                    )} """)
                    db_data = to_connect.fetchone(f""" select * from {to_db}.{tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1
        to_connect.execute(f""" update {to_db}.{tabel_name} set num=null where num=-1 """)

        print(f'【{tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    def migration_project_env():
        tabel_name = 'web_ui_test_project_env'
        count, start_at = 0, datetime.datetime.now()
        print(f'开始执行【{tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{tabel_name} (
                        id, create_time, update_time, create_user, update_user, host, variables, env_id, project_id
                    )  values {(
                        data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                        data["host"], data["variables"], data["env_id"], data["project_id"]
                    )} """)
                    db_data = to_connect.fetchone(f""" select * from {to_db}.{tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1

        print(f'【{tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    def migration_module():
        tabel_name = 'web_ui_test_module'
        count, start_at = 0, datetime.datetime.now()
        print(f'开始执行【{tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{tabel_name} (
                        id, create_time, update_time, create_user, update_user, name, num, parent, project_id
                    )  values {(
                        data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                        data["name"], -1 if data["num"] is None else data["num"], data["parent"] or -1, data["project_id"]
                    )} """)
                    db_data = to_connect.fetchone(f""" select * from {to_db}.{tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1

        to_connect.execute(f""" update {to_db}.{tabel_name} set num=null where num=-1 """)
        to_connect.execute(f""" update {to_db}.{tabel_name} set parent=null where parent=-1 """)
        to_connect.execute(f""" update {to_db}.{tabel_name} set controller=null where controller='' """)

        print(f'【{tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    def migration_page():
        tabel_name = 'web_ui_test_page'
        count, start_at = 0, datetime.datetime.now()
        print(f'开始执行【{tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{tabel_name} (
                        id, create_time, update_time, create_user, update_user, 
                        name, num, `desc`, project_id, module_id, addr
                    )  values {(
                        data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                        data["name"], -1 if data["num"] is None else data["num"], data["desc"] or '',
                        data["project_id"], data["module_id"], data["addr"] or ''
                    )} """)
                    db_data = to_connect.fetchone(f""" select * from {to_db}.{tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1

        to_connect.execute(f""" update {to_db}.{tabel_name} set num=null where num=-1 """)

        print(f'【{tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    def migration_element():
        tabel_name = 'web_ui_test_element'
        count, start_at = 0, datetime.datetime.now()
        print(f'开始执行【{tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{tabel_name} (
                        id, create_time, update_time, create_user, update_user, 
                        name, num, `desc`, project_id, module_id, `by`, element, wait_time_out, page_id
                    )  values {(
                        data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                        data["name"], -1 if data["num"] is None else data["num"], data["desc"] or '',
                        data["project_id"], data["module_id"], data["by"], data["element"], data["wait_time_out"], data["page_id"]
                    )} """)
                    db_data = to_connect.fetchone(f""" select * from {to_db}.{tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1

        to_connect.execute(f""" update {to_db}.{tabel_name} set num=null where num=-1 """)

        print(f'【{tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    def migration_case_suite():
        tabel_name = 'web_ui_test_case_suite'
        count, start_at = 0, datetime.datetime.now()
        print(f'开始执行【{tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{tabel_name} (
                        id, create_time, update_time, create_user, update_user, name, num, parent, project_id, 
                        suite_type
                    )  values {(
                        data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                        data["name"], -1 if data["num"] is None else data["num"], data["parent"] or -1, data["project_id"],
                        "make_data" if data["suite_type"] == "assist" else data["suite_type"]
                    )} """)
                    db_data = to_connect.fetchone(f""" select * from {to_db}.{tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1

        to_connect.execute(f""" update {to_db}.{tabel_name} set num=null where num=-1 """)
        to_connect.execute(f""" update {to_db}.{tabel_name} set parent=null where parent=-1 """)

        print(f'【{tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    def migration_case():
        tabel_name = 'web_ui_test_case'
        count, start_at = 0, datetime.datetime.now()
        print(f'开始执行【{tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{tabel_name} (
                        id, create_time, update_time, create_user, update_user,
                        name, num, `desc`, status, run_times, script_list, 
                        variables, output, skip_if, suite_id
                    )  values {(
                        data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                        data["name"], -1 if data["num"] is None else data["num"], data["desc"] or '', data["status"], data["run_times"], data["script_list"],
                        data["variables"], data["output"], data["skip_if"], data["suite_id"]
                    )} """)

                    db_data = to_connect.fetchone(f""" select * from {to_db}.{tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1

        to_connect.execute(f""" update {to_db}.{tabel_name} set num=0 where num=-1 """)
        to_connect.execute(f""" update {to_db}.{tabel_name} set `desc`=null where `desc`='' """)

        print(f'【{tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    def migration_step():
        tabel_name = 'web_ui_test_step'
        count, start_at = 0, datetime.datetime.now()
        print(f'开始执行【{tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{tabel_name} (
                        id, create_time, update_time, create_user, update_user, 
                        name, num, status, run_times, up_func, down_func, 
                        skip_if, skip_on_fail, data_driver, quote_case, case_id, 
                        wait_time_out, execute_type, send_keys, extracts, validates, element_id
                    )  values {(
                        data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                        data["name"], -1 if data["num"] is None else data["num"], "disable" if data["status"] == 0 else "enable", data["run_times"], data["up_func"] if data["up_func"] else '[]', data["down_func"] if data["down_func"] else '[]',
                        data["skip_if"], data["skip_on_fail"], '[]' if data["data_driver"] in [None, 'null'] else data["data_driver"], data["quote_case"] or -1, data["case_id"],
                        data["wait_time_out"], data["execute_type"] or '', data["send_keys"] or '', data["extracts"], data["validates"], data["element_id"] or -1
                    )} """)

                    db_data = to_connect.fetchone(f""" select * from {to_db}.{tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1

        to_connect.execute(f""" update {to_db}.{tabel_name} set `element_id`=null where `element_id`=-1 """)
        to_connect.execute(f""" update {to_db}.{tabel_name} set `quote_case`=null where `quote_case`=-1 """)
        to_connect.execute(f""" update {to_db}.{tabel_name} set `send_keys`=null where `send_keys`='' """)
        to_connect.execute(f""" update {to_db}.{tabel_name} set `execute_type`=null where `execute_type`='' """)

        print(f'【{tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    def migration_task():
        tabel_name = 'web_ui_test_task'
        count, start_at = 0, datetime.datetime.now()
        print(f'开始执行【{tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{tabel_name} (
                        id, create_time, update_time, create_user, update_user,
                        name, num, env_list, case_ids, task_type, cron, 
                        is_send, 
                        receive_type, webhook_list, email_server, email_from, 
                        email_pwd, email_to, status, is_async, suite_ids, 
                        call_back, project_id, conf, skip_holiday
                    )  values {(
                        data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                        data["name"], -1 if data["num"] is None else data["num"], data["env_list"], data["case_ids"], data["task_type"], data["cron"],
                        "not_send" if data["is_send"] == "1" else "always" if data["is_send"] == "2" else "on_fail",
                        data["receive_type"] or '', data["webhook_list"] or '[]', data["email_server"], data["email_from"],
                        data["email_pwd"], data["email_to"] or '[]', "disable" if data["status"] == 0 else "enable", 0, data["suite_ids"],
                        data["call_back"] or '[]', data["project_id"], '{}' if data["conf"] is None or data["conf"] == 'null' else data["conf"], 1
                    )} """)

                    db_data = to_connect.fetchone(f""" select * from {to_db}.{tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1

        to_connect.execute(f""" update {to_db}.{tabel_name} set conf='{json.dumps({})}' where conf='null' """)
        to_connect.execute(f""" update {to_db}.{tabel_name} set num=0 where num=-1 """)
        to_connect.execute(f""" update {to_db}.{tabel_name} set `receive_type`=null where `receive_type`='' """)

        print(f'【{tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    def migration_report():
        tabel_name = 'web_ui_test_report'
        count, start_at = 0, datetime.datetime.now()
        print(f'开始执行【{tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{tabel_name} (
                        id, create_time, update_time, create_user, update_user,
                        name, status, is_passed, run_type, project_id, 
                        env,  trigger_type, process, retry_count, run_id, 
                        temp_variables, batch_id, summary
                    )  values {(
                        data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                        data["name"], data["status"], data["is_passed"], data["run_type"], data["project_id"],
                        data["env"], data["trigger_type"], data["process"], data["retry_count"], data["run_id"],
                        format_temp_variables(data["temp_variables"]), data["batch_id"], format_report_summary(json.loads(data["summary"]))
                    )} """)

                    db_data = to_connect.fetchone(f""" select * from {to_db}.{tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1
            print(f'{max_id["max(id)"]} => {i}')
        print(f'【{tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    def migration_report_case():
        tabel_name = 'web_ui_test_report_case'
        count, start_at = 0, datetime.datetime.now()
        print(f'开始执行【{tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{tabel_name} (
                        id, create_time, update_time, create_user, update_user,
                        name, case_id, report_id, result, case_data, 
                        summary,  error_msg
                    )  values {(
                        data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                        data["name"], data["from_id"], data["report_id"], data["result"], data["case_data"],
                        format_report_case_summary(json.loads(data["summary"])), data["error_msg"] or ''
                    )} """)

                    db_data = to_connect.fetchone(f""" select * from {to_db}.{tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1
                print(f'{max_id["max(id)"]} => {i}')
        print(f'【{tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    def migration_report_step():
        tabel_name = 'web_ui_test_report_step'
        count, start_at = 0, datetime.datetime.now()
        print(f'开始执行【{tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{tabel_name} (
                        id, create_time, update_time, create_user, update_user,
                        name, case_id, step_id, report_case_id, report_id, 
                        process, result, step_data, summary, element_id
                    )  values {(
                        data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                        data["name"], data["case_id"] or -1, data["step_id"] or -1, data["report_case_id"], data["report_id"],
                        data["process"], data["result"], format_step_data(data["step_data"]), format_report_step_summary(json.loads(data["summary"])), data["from_id"]
                    )} """)

                    db_data = to_connect.fetchone(f""" select * from {to_db}.{tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1
                print(f'{max_id["max(id)"]} => {i}')
        to_connect.execute(f""" update {to_db}.{tabel_name} set step_id=null where step_id=-1 """)
        to_connect.execute(f""" update {to_db}.{tabel_name} set case_id=null where case_id=-1 """)
        print(f'【{tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    send_msg({
        "ui_project": migration_project(),
        "ui_project_env": migration_project_env(),
        "ui_module": migration_module(),
        "ui_page": migration_page(),
        "ui_element": migration_element(),
        "ui_case_suite": migration_case_suite(),
        "ui_case": migration_case(),
        "ui_step": migration_step(),
        "ui_task": migration_task(),
        "ui_report": migration_report(),
        "ui_report_case": migration_report_case(),
        "ui_report_step": migration_report_step()
    })


def migration_app_test():
    def migration_project():
        tabel_name = 'app_ui_test_project'
        count, start_at = 0, datetime.datetime.now()
        print(f'开始执行【{tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{tabel_name} (
                        id, create_time, update_time, create_user, update_user, 
                        name, manager, script_list, num, business_id,
                        app_package, app_activity, template_device
                    )  values {(
                        data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                        data["name"], data["manager"], data["script_list"], -1 if data["num"] is None else data["num"], data["business_id"],
                        data["app_package"], data["app_activity"], data["template_device"],
                    )} """)
                    db_data = to_connect.fetchone(f""" select * from {to_db}.{tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1
        to_connect.execute(f""" update {to_db}.{tabel_name} set num=null where num=-1 """)

        print(f'【{tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    def migration_project_env():
        tabel_name = 'app_ui_test_project_env'
        count, start_at = 0, datetime.datetime.now()
        print(f'开始执行【{tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{tabel_name} (
                        id, create_time, update_time, create_user, update_user, host, variables, env_id, project_id
                    )  values {(
                        data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                        data["host"], data["variables"], data["env_id"], data["project_id"]
                    )} """)
                    db_data = to_connect.fetchone(f""" select * from {to_db}.{tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1

        print(f'【{tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    def migration_module():
        tabel_name = 'app_ui_test_module'
        count, start_at = 0, datetime.datetime.now()
        print(f'开始执行【{tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{tabel_name} (
                        id, create_time, update_time, create_user, update_user, name, num, parent, project_id
                    )  values {(
                        data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                        data["name"], -1 if data["num"] is None else data["num"], data["parent"] or -1, data["project_id"]
                    )} """)
                    db_data = to_connect.fetchone(f""" select * from {to_db}.{tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1

        to_connect.execute(f""" update {to_db}.{tabel_name} set num=null where num=-1 """)
        to_connect.execute(f""" update {to_db}.{tabel_name} set parent=null where parent=-1 """)

        print(f'【{tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    def migration_page():
        tabel_name = 'app_ui_test_page'
        count, start_at = 0, datetime.datetime.now()
        print(f'开始执行【{tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{tabel_name} (
                        id, create_time, update_time, create_user, update_user, 
                        name, num, `desc`, project_id, module_id
                    )  values {(
                        data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                        data["name"], -1 if data["num"] is None else data["num"], data["desc"] or '',
                        data["project_id"], data["module_id"]
                    )} """)
                    db_data = to_connect.fetchone(f""" select * from {to_db}.{tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1

        to_connect.execute(f""" update {to_db}.{tabel_name} set num=null where num=-1 """)
        print(f'【{tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    def migration_element():
        tabel_name = 'app_ui_test_element'
        count, start_at = 0, datetime.datetime.now()
        print(f'开始执行【{tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{tabel_name} (
                        id, create_time, update_time, create_user, update_user, 
                        name, num, `desc`, project_id, module_id, `by`, element, wait_time_out, page_id, template_device
                    )  values {(
                        data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                        data["name"], -1 if data["num"] is None else data["num"], data["desc"] or '',
                        data["project_id"], data["module_id"], data["by"], data["element"],
                        data["wait_time_out"], data["page_id"], data["template_device"]
                    )} """)
                    db_data = to_connect.fetchone(f""" select * from {to_db}.{tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1

        to_connect.execute(f""" update {to_db}.{tabel_name} set num=null where num=-1 """)
        print(f'【{tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    def migration_case_suite():
        tabel_name = 'app_ui_test_case_suite'
        count, start_at = 0, datetime.datetime.now()
        print(f'开始执行【{tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{tabel_name} (
                        id, create_time, update_time, create_user, update_user, name, num, parent, project_id, 
                        suite_type
                    )  values {(
                        data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                        data["name"], -1 if data["num"] is None else data["num"], data["parent"] or -1, data["project_id"],
                        "make_data" if data["suite_type"] == "assist" else data["suite_type"]
                    )} """)
                    db_data = to_connect.fetchone(f""" select * from {to_db}.{tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1

        to_connect.execute(f""" update {to_db}.{tabel_name} set num=null where num=-1 """)
        to_connect.execute(f""" update {to_db}.{tabel_name} set parent=null where parent=-1 """)
        print(f'【{tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    def migration_case():
        tabel_name = 'app_ui_test_case'
        count, start_at = 0, datetime.datetime.now()
        print(f'开始执行【{tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{tabel_name} (
                        id, create_time, update_time, create_user, update_user,
                        name, num, `desc`, status, run_times, script_list, 
                        variables, output, skip_if, suite_id
                    )  values {(
                        data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                        data["name"], -1 if data["num"] is None else data["num"], data["desc"] or '', data["status"], data["run_times"], data["script_list"],
                        data["variables"], data["output"], data["skip_if"], data["suite_id"]
                    )} """)

                    db_data = to_connect.fetchone(f""" select * from {to_db}.{tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1

        to_connect.execute(f""" update {to_db}.{tabel_name} set num=0 where num=-1 """)
        to_connect.execute(f""" update {to_db}.{tabel_name} set `desc`=null where `desc`='' """)
        print(f'【{tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    def migration_step():
        tabel_name = 'app_ui_test_step'
        count, start_at = 0, datetime.datetime.now()
        print(f'开始执行【{tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{tabel_name} (
                        id, create_time, update_time, create_user, update_user, 
                        name, num, status, run_times, up_func, down_func, 
                        skip_if, skip_on_fail, data_driver, quote_case, case_id, 
                        wait_time_out, execute_type, send_keys, extracts, validates, element_id
                    )  values {(
                        data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                        data["name"], -1 if data["num"] is None else data["num"], "disable" if data["status"] == 0 else "enable", data["run_times"], data["up_func"] if data["up_func"] else '[]', data["down_func"] if data["down_func"] else '[]',
                        data["skip_if"], 0 if data["skip_on_fail"] is None else data["skip_on_fail"], '[]' if data["data_driver"] in [None, 'null'] else data["data_driver"], data["quote_case"] or -1, data["case_id"],
                        data["wait_time_out"], data["execute_type"] or '', data["send_keys"] or '', data["extracts"], data["validates"], data["element_id"] or -1
                    )} """)

                    db_data = to_connect.fetchone(f""" select * from {to_db}.{tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1
        to_connect.execute(f""" update {to_db}.{tabel_name} set `element_id`=null where `element_id`=-1 """)
        to_connect.execute(f""" update {to_db}.{tabel_name} set `quote_case`=null where `quote_case`=-1 """)
        to_connect.execute(f""" update {to_db}.{tabel_name} set `send_keys`=null where `send_keys`='' """)
        to_connect.execute(f""" update {to_db}.{tabel_name} set `execute_type`=null where `execute_type`='' """)
        print(f'【{tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    def migration_task():
        tabel_name = 'app_ui_test_task'
        count, start_at = 0, datetime.datetime.now()
        print(f'开始执行【{tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{tabel_name} (
                        id, create_time, update_time, create_user, update_user,
                        name, num, env_list, case_ids, task_type, cron, 
                        is_send, 
                        receive_type, webhook_list, email_server, email_from, 
                        email_pwd, email_to, status, is_async, suite_ids, 
                        call_back, project_id, conf, skip_holiday
                    )  values {(
                        data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                        data["name"], -1 if data["num"] is None else data["num"], f'["{data["env_list"]}"]', data["case_ids"], data["task_type"], data["cron"],
                        "not_send" if data["is_send"] == "1" else "always" if data["is_send"] == "2" else "on_fail",
                        data["receive_type"] or '', data["webhook_list"] or '[]', data["email_server"], data["email_from"],
                        data["email_pwd"], data["email_to"] or '[]', "disable" if data["status"] == 0 else "enable", 0, data["suite_ids"],
                        data["call_back"] or '[]', data["project_id"], '{}' if data["conf"] is None or data["conf"] == 'null' else data["conf"], 1
                    )} """)

                    db_data = to_connect.fetchone(f""" select * from {to_db}.{tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1

        to_connect.execute(f""" update {to_db}.{tabel_name} set conf='{json.dumps({})}' where conf='null' """)
        to_connect.execute(f""" update {to_db}.{tabel_name} set num=0 where num=-1 """)
        to_connect.execute(f""" update {to_db}.{tabel_name} set `receive_type`=null where `receive_type`='' """)
        print(f'【{tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    def migration_report():
        tabel_name = 'app_ui_test_report'
        count, start_at = 0, datetime.datetime.now()
        print(f'开始执行【{tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{tabel_name} (
                        id, create_time, update_time, create_user, update_user,
                        name, status, is_passed, run_type, project_id, 
                        env,  trigger_type, process, retry_count, run_id, 
                        temp_variables, batch_id, summary
                    )  values {(
                        data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                        data["name"], data["status"], data["is_passed"], data["run_type"], data["project_id"],
                        data["env"], data["trigger_type"], data["process"], data["retry_count"], data["run_id"],
                        format_temp_variables(data["temp_variables"]), data["batch_id"], format_report_summary(json.loads(data["summary"]))
                    )} """)

                    db_data = to_connect.fetchone(f""" select * from {to_db}.{tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1
                print(f'{max_id["max(id)"]} => {i}')
        print(f'【{tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    def migration_report_case():
        tabel_name = 'app_ui_test_report_case'
        count, start_at = 0, datetime.datetime.now()
        print(f'开始执行【{tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{tabel_name} (
                        id, create_time, update_time, create_user, update_user,
                        name, case_id, report_id, result, case_data, 
                        summary,  error_msg
                    )  values {(
                        data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                        data["name"], data["from_id"], data["report_id"], data["result"], data["case_data"],
                        format_report_case_summary(json.loads(data["summary"])), data["error_msg"] or ''
                    )} """)

                    db_data = to_connect.fetchone(f""" select * from {to_db}.{tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1
                print(f'{max_id["max(id)"]} => {i}')
        print(f'【{tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    def migration_report_step():
        tabel_name = 'app_ui_test_report_step'
        count, start_at = 0, datetime.datetime.now()
        print(f'开始执行【{tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{tabel_name} (
                        id, create_time, update_time, create_user, update_user,
                        name, case_id, step_id, report_case_id, report_id, 
                        process, result, step_data, summary, element_id
                    )  values {(
                        data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                        data["name"], data["case_id"] or -1, data["step_id"] or -1, data["report_case_id"], data["report_id"],
                        data["process"], data["result"], format_step_data(data["step_data"]), format_report_step_summary(json.loads(data["summary"])), data["from_id"]
                    )} """)

                    db_data = to_connect.fetchone(f""" select * from {to_db}.{tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1
                print(f'{max_id["max(id)"]} => {i}')
        to_connect.execute(f""" update {to_db}.{tabel_name} set step_id=null where step_id=-1 """)
        to_connect.execute(f""" update {to_db}.{tabel_name} set case_id=null where case_id=-1 """)
        print(f'【{tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    send_msg({
        "app_project": migration_project(),
        "app_project_env": migration_project_env(),
        "app_module": migration_module(),
        "app_page": migration_page(),
        "app_element": migration_element(),
        "app_case_suite": migration_case_suite(),
        "app_case": migration_case(),
        "app_step": migration_step(),
        "app_task": migration_task(),
        "app_report": migration_report(),
        "app_report_case": migration_report_case(),
        "app_report_step": migration_report_step(),
    })


def migration_auto_test():
    def migration_auto_test_hits():
        tabel_name = 'auto_test_hits'
        count, start_at = 0, datetime.datetime.now()
        print(f'开始执行【{tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{tabel_name} (
                        id, create_time, update_time, create_user, update_user,
                        date, hit_type, hit_detail, test_type, report_id, `desc` , 
                        project_id, env
                    )  values {(
                        data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                        data["date"], data["hit_type"], data["hit_detail"], data["test_type"], data["report_id"],
                        data["desc"] or '', data["project_id"], data["env"]
                    )} """)

                    db_data = to_connect.fetchone(f""" select * from {to_db}.{tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1

        print(f'【{tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    def migration_auto_test_user():
        tabel_name = 'auto_test_user'
        count, start_at = 0, datetime.datetime.now()
        print(f'开始执行【{tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{tabel_name} (
                        id, create_time, update_time, create_user, update_user,
                        mobile, company_name, access_token, refresh_token, user_id,
                        company_id, password, role, env
                    )  values {(
                        data["id"], data["created_time"] or get_now(), data["update_time"] or get_now(), data["create_user"] or -1, data["update_user"] or data["create_user"] or -1,
                        data["mobile"], data["company_name"] or '', data["access_token"], data["refresh_token"], data["user_id"] or '',
                        data["company_id"] or '', data["password"] or '', data["role"] or '', data["env"]
                    )} """)

                    db_data = to_connect.fetchone(f""" select * from {to_db}.{tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1

        to_connect.execute(f""" update {to_db}.{tabel_name} set `create_user`=null where `create_user`=-1 """)
        to_connect.execute(f""" update {to_db}.{tabel_name} set `update_user`=null where `update_user`=-1 """)
        print(f'【{tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    def migration_func_error_record():
        tabel_name = 'func_error_record'
        count, start_at = 0, datetime.datetime.now()
        print(f'开始执行【{tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{tabel_name} (
                        id, create_time, update_time, create_user, update_user,
                        name, detail
                    )  values {(
                        data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                        data["name"], data["detail"]
                    )} """)

                    db_data = to_connect.fetchone(f""" select * from {to_db}.{tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1

        print(f'【{tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    def migration_python_script():
        from_tabel_name = 'python_script'
        count, start_at = 0, datetime.datetime.now()
        to_tabel_name = 'auto_test_python_script'
        print(f'开始执行【{from_tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{to_tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{from_tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{from_tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{from_tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{to_tabel_name} (
                        id, create_time, update_time, create_user, update_user,
                        name, script_data, `desc`, num, script_type
                    )  values {(
                        data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                        data["name"], data["script_data"], data["desc"], -1 if data["num"] is None else data["num"], data["script_type"]
                    )} """)

                    db_data = to_connect.fetchone(f""" select * from {to_db}.{to_tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1

        to_connect.execute(f""" update {to_db}.{to_tabel_name} set num=0 where num=-1 """)
        print(f'【{from_tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    def migration_swagger_pull_log():
        from_tabel_name = 'swagger_pull_log'
        count, start_at = 0, datetime.datetime.now()
        to_tabel_name = 'auto_test_swagger_pull_log'
        print(f'开始执行【{from_tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{to_tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{from_tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{from_tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{from_tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{to_tabel_name} (
                        id, create_time, update_time, create_user, update_user,
                        status, project_id, `desc`, pull_args
                    )  values {(
                        data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                        data["status"], data["project_id"], data["desc"] or '', data["pull_args"] or '[]'
                    )} """)

                    db_data = to_connect.fetchone(f""" select * from {to_db}.{to_tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1

        to_connect.execute(f""" update {to_db}.{to_tabel_name} set `desc`=null where `desc`='' """)
        print(f'【{from_tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    def migration_test_work_account():
        tabel_name = 'test_work_env'
        count, start_at = 0, datetime.datetime.now()
        print(f'开始执行【{tabel_name}】数据迁移')
        to_connect.execute(f""" truncate {to_db}.{tabel_name}; """)
        max_id = from_connect.fetchone(f""" select max(id) from {from_db}.{tabel_name} """)
        min_id = from_connect.fetchone(f""" select min(id) from {from_db}.{tabel_name} """)
        if max_id["max(id)"] and max_id["max(id)"] > 0:
            for i in range(max_id["max(id)"] + 1):
                if i < min_id["min(id)"]:
                    continue
                data = from_connect.fetchone(f""" select * from {from_db}.{tabel_name} where id={i} """)
                if data:
                    to_connect.execute(f""" insert into {to_db}.{tabel_name} (
                        id, create_time, update_time, create_user, update_user,
                        business, name, num, source_type, 
                        value, password, `desc`, parent
                    )  values {(
                        data["id"], data["created_time"], data["update_time"], data["create_user"], data["update_user"] or data["create_user"],
                        data["business"] or -1, data["name"], -1 if data["num"] is None else data["num"], data["source_type"],
                        data["value"], data["password"], data["desc"] or '', data["parent"] or -1
                    )} """)

                    db_data = to_connect.fetchone(f""" select * from {to_db}.{tabel_name} where id={data["id"]} """)
                    assert db_data["id"]
                    count += 1

        to_connect.execute(f""" update {to_db}.{tabel_name} set `desc`=null where `desc`='' """)
        to_connect.execute(f""" update {to_db}.{tabel_name} set `business`=null where `business`=-1 """)
        to_connect.execute(f""" update {to_db}.{tabel_name} set `parent`=null where `parent`=-1 """)
        print(f'【{tabel_name}】数据迁移完毕')
        end_at = datetime.datetime.now()
        return {"start_at": start_at, "end_at": end_at, "count": count}

    send_msg({
        "auto_test_hits": migration_auto_test_hits(),
        "auto_test_user": migration_auto_test_user(),
        "func_error_record": migration_func_error_record(),
        "python_script": migration_python_script(),
        "swagger_pull_log": migration_swagger_pull_log(),
        "test_work_account": migration_test_work_account()
    })


if __name__ == '__main__':
    threading.Thread(target=migration_system).start()
    threading.Thread(target=migration_config).start()
    threading.Thread(target=migration_auto_test).start()
    threading.Thread(target=migration_api_test).start()
    threading.Thread(target=migration_ui_test).start()
    threading.Thread(target=migration_app_test).start()

    # nohup python3.9 flast_db_to_fastapi.py & tail -f nohup.out
