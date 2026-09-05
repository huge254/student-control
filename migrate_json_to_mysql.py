# -*- coding: utf-8 -*-
"""数据迁移脚本：data.json → MySQL

用法：python migrate_json_to_mysql.py
说明：
  - 读取项目目录下的 data.json（旧 JSON 版数据）
  - 导入 MySQL 的 student_management 库
  - 幂等：表中已有数据时跳过对应表的导入，可安全重复运行
  - 密码哈希原样迁移，无需重置任何账号密码
"""
import json
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, select, URL
from sqlalchemy.orm import sessionmaker

from models import Base, Grade, Request, Student, Teacher

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

DB_HOST = os.environ.get("DB_HOST", "127.0.0.1")
DB_PORT = int(os.environ.get("DB_PORT", "3306"))
DB_USER = os.environ.get("DB_USER", "sms_app")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_NAME = os.environ.get("DB_NAME", "student_management")

if not DB_PASSWORD:
    raise SystemExit("缺少数据库密码：请在项目目录的 .env 文件中配置 DB_PASSWORD")

json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")

if not os.path.exists(json_path):
    raise SystemExit("未找到 data.json，无需迁移")

with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

url = URL.create(drivername="mysql+pymysql", username=DB_USER,
                 password=DB_PASSWORD, host=DB_HOST, port=DB_PORT,
                 database=DB_NAME)
engine = create_engine(url)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

imported = []
with Session() as session:
    # 教师
    if session.scalar(select(Teacher.id).limit(1)) is None:
        for t in data.get("teachers", []):
            session.add(Teacher(id=t["id"], name=t["name"], role=t["role"],
                                salt=t["salt"], password_hash=t["password_hash"]))
        imported.append(f"教师 {len(data.get('teachers', []))} 人")
    else:
        imported.append("教师表已有数据，跳过")

    # 学生（含成绩）
    if session.scalar(select(Student.id).limit(1)) is None:
        for s in data.get("students", []):
            stu = Student(id=s["id"], name=s["name"], gender=s["gender"],
                          class_name=s["class_name"], phone=s["phone"],
                          salt=s["salt"], password_hash=s["password_hash"])
            for sub, score in s.get("grades", {}).items():
                stu.grades.append(Grade(subject=sub, score=int(score)))
            session.add(stu)
        imported.append(f"学生 {len(data.get('students', []))} 人")
    else:
        imported.append("学生表已有数据，跳过")

    # 修改申请
    if session.scalar(select(Request.req_id).limit(1)) is None:
        reqs = data.get("requests", [])
        for r in reqs:
            session.add(Request(req_id=r["req_id"], student_id=r["student_id"],
                                student_name=r["student_name"], field=r["field"],
                                field_label=r["field_label"],
                                old_value=r["old_value"], new_value=r["new_value"],
                                status=r["status"], time=r["time"]))
        imported.append(f"申请记录 {len(reqs)} 条")
    else:
        imported.append("申请表已有数据，跳过")

    session.commit()

print("迁移完成：")
for line in imported:
    print("  -", line)
