# -*- coding: utf-8 -*-
"""学生管理系统 - 数据层（MySQL 数据库）

- 通过 SQLAlchemy ORM 读写 MySQL（库名 student_management）
- 对外保持与旧 JSON 版完全相同的接口：Database 类的方法签名不变，
  main.py 因此无需任何改动
- db.data 以属性形式返回 {teachers, students, requests} 字典视图（只读展示用）
- 密码仍为「随机盐 + SHA256」，不保存明文
"""
import hashlib
import json
import os
import secrets
import time
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import create_engine, select
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session, selectinload, sessionmaker

from models import Base, Grade, Request, Student, Teacher

# 加载项目根目录的 .env 配置文件（数据库密码等敏感信息不写在代码里）
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

# ---------- 数据库连接配置（.env 优先，环境变量可覆盖） ----------
DB_HOST = os.environ.get("DB_HOST", "127.0.0.1")
DB_PORT = int(os.environ.get("DB_PORT", "3306"))
DB_USER = os.environ.get("DB_USER", "sms_app")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_NAME = os.environ.get("DB_NAME", "student_management")

if not DB_PASSWORD:
    raise SystemExit("缺少数据库密码：请在项目目录的 .env 文件中配置 DB_PASSWORD")

_url = URL.create(
    drivername="mysql+pymysql",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME,
)

# 学生信息中允许学生发起修改申请的字段（key -> 中文名）
EDITABLE_FIELDS = {
    'phone': '电话',
    'gender': '性别',
    'class_name': '班级',
    'name': '姓名',
}

Record = dict[str, Any]


def _hash_pwd(password: str, salt: str) -> str:
    """加盐哈希"""
    return hashlib.sha256((salt + password).encode('utf-8')).hexdigest()


def _teacher_dict(t: Teacher) -> Record:
    return {'id': t.id, 'name': t.name, 'role': t.role,
            'salt': t.salt, 'password_hash': t.password_hash}


def _student_dict(s: Student) -> Record:
    return {'id': s.id, 'name': s.name, 'gender': s.gender,
            'class_name': s.class_name, 'phone': s.phone,
            'salt': s.salt, 'password_hash': s.password_hash,
            'grades': {g.subject: g.score for g in s.grades}}


def _request_dict(r: Request) -> Record:
    return {'req_id': r.req_id, 'student_id': r.student_id,
            'student_name': r.student_name, 'field': r.field,
            'field_label': r.field_label, 'old_value': r.old_value,
            'new_value': r.new_value, 'status': r.status, 'time': r.time}


class Database:
    """MySQL 数据库：封装全部业务操作，接口与旧 JSON 版一致"""

    def __init__(self, path: str | None = None):
        self.engine = create_engine(_url, pool_pre_ping=True)
        Base.metadata.create_all(self.engine)
        self._Session = sessionmaker(bind=self.engine, expire_on_commit=False)
        self._seed_if_empty()

    # ---------- 默认数据 ----------
    def _seed_if_empty(self) -> None:
        with self._Session() as session:
            if session.scalar(select(Teacher.id).limit(1)) is not None:
                return
            seed = self._default_seed()
            for t in seed['teachers']:
                session.add(Teacher(id=t['id'], name=t['name'], role=t['role'],
                                    salt=t['salt'], password_hash=t['password_hash']))
            for s in seed['students']:
                stu = Student(id=s['id'], name=s['name'], gender=s['gender'],
                              class_name=s['class_name'], phone=s['phone'],
                              salt=s['salt'], password_hash=s['password_hash'])
                for sub, score in s['grades'].items():
                    stu.grades.append(Grade(subject=sub, score=score))
                session.add(stu)
            session.commit()

    @staticmethod
    def _default_seed() -> dict[str, Any]:
        def make_teacher(tid, name, role, pwd):
            salt = secrets.token_hex(8)
            return {'id': tid, 'name': name, 'role': role, 'salt': salt,
                    'password_hash': _hash_pwd(pwd, salt)}

        def make_student(sid, name, gender, class_name, phone, pwd, grades):
            salt = secrets.token_hex(8)
            return {'id': sid, 'name': name, 'gender': gender,
                    'class_name': class_name, 'phone': phone, 'salt': salt,
                    'password_hash': _hash_pwd(pwd, salt), 'grades': grades}

        return {
            'teachers': [
                make_teacher('admin', '系统管理员', 'admin', 'admin123'),
                make_teacher('t001', '李老师', 'teacher', '123456'),
            ],
            'students': [
                make_student('2024001', '张三', '男', '计算机2401', '13800000001',
                             '123456', {'语文': 90, '数学': 85, '英语': 88}),
                make_student('2024002', '李四', '女', '计算机2401', '13800000002',
                             '123456', {'语文': 76, '数学': 92, '英语': 81}),
                make_student('2024003', '王五', '男', '软件2402', '13800000003',
                             '123456', {'语文': 88, '数学': 79, '英语': 93}),
            ],
            'requests': [],
        }

    # ---------- 只读字典视图（兼容 main.py 直接访问） ----------
    @property
    def data(self) -> dict[str, Any]:
        with self._Session() as session:
            return {
                'teachers': [_teacher_dict(t) for t in session.scalars(select(Teacher))],
                'students': [_student_dict(s) for s in
                             session.scalars(select(Student).options(
                                 selectinload(Student.grades)))],
                'requests': [_request_dict(r) for r in session.scalars(select(Request))],
            }

    # ---------- 查询 ----------
    def find_teacher(self, tid: str) -> Record | None:
        with self._Session() as session:
            t = session.get(Teacher, tid)
            return _teacher_dict(t) if t else None

    def find_student(self, sid: str) -> Record | None:
        with self._Session() as session:
            s = session.get(Student, sid)
            return _student_dict(s) if s else None

    def verify(self, record: Record, password: str) -> bool:
        return _hash_pwd(password, record['salt']) == record['password_hash']

    @staticmethod
    def is_admin(teacher: Record) -> bool:
        return teacher.get('role') == 'admin'

    # ---------- 登录校验 ----------
    def teacher_login(self, tid: str, password: str) -> tuple[Record | None, str | None]:
        if self.find_student(tid):
            return None, '该账号是学生账号，请点击「学生登录」按钮'
        t = self.find_teacher(tid)
        if t is None:
            return None, '教师账号不存在'
        if not self.verify(t, password):
            return None, '密码错误'
        return t, None

    def student_login(self, sid: str, password: str) -> tuple[Record | None, str | None]:
        if self.find_teacher(sid):
            return None, '该账号是教师账号，请点击「教师登录」按钮'
        s = self.find_student(sid)
        if s is None:
            return None, '学生账号不存在'
        if not self.verify(s, password):
            return None, '密码错误'
        return s, None

    # ---------- 学生管理 ----------
    def add_student(self, sid: str, name: str, gender: str, class_name: str,
                    phone: str, password: str,
                    grades: dict[str, Any] | None = None) -> tuple[bool, str]:
        if self.find_student(sid):
            return False, '学号已存在'
        if self.find_teacher(sid):
            return False, '该账号已被教师账号占用'
        salt = secrets.token_hex(8)
        with self._Session() as session:
            stu = Student(id=sid, name=name, gender=gender, class_name=class_name,
                          phone=phone, salt=salt,
                          password_hash=_hash_pwd(password, salt))
            for sub, score in (grades or {}).items():
                stu.grades.append(Grade(subject=sub, score=score))
            session.add(stu)
            session.commit()
        return True, '学生添加成功'

    def delete_student(self, sid: str) -> tuple[bool, str]:
        with self._Session() as session:
            s = session.get(Student, sid)
            if s is None:
                return False, '学生不存在'
            session.delete(s)
            for r in session.scalars(
                    select(Request).where(Request.student_id == sid)):
                session.delete(r)
            session.commit()
        return True, '学生已删除'

    def update_student_info(self, sid: str, name: str | None = None,
                            gender: str | None = None, class_name: str | None = None,
                            phone: str | None = None) -> tuple[bool, str]:
        with self._Session() as session:
            s = session.get(Student, sid)
            if s is None:
                return False, '学生不存在'
            if name is not None:
                s.name = name
            if gender is not None:
                s.gender = gender
            if class_name is not None:
                s.class_name = class_name
            if phone is not None:
                s.phone = phone
            session.commit()
        return True, '学生信息已更新'

    def set_grades(self, sid: str, grades: dict[str, Any]) -> tuple[bool, str]:
        """整表覆盖某学生的成绩"""
        clean = {k: int(v) for k, v in grades.items() if v is not None and v != ''}
        if any(not (0 <= v <= 100) for v in clean.values()):
            return False, '分数必须在 0~100 之间'
        with self._Session() as session:
            s = session.get(Student, sid)
            if s is None:
                return False, '学生不存在'
            for g in list(s.grades):
                session.delete(g)
            for sub, score in clean.items():
                session.add(Grade(student_id=sid, subject=sub, score=score))
            session.commit()
        return True, '成绩已保存'

    # ---------- 教师账号管理（仅管理员） ----------
    def add_teacher(self, tid: str, name: str, password: str) -> tuple[bool, str]:
        if self.find_teacher(tid):
            return False, '教师工号已存在'
        if self.find_student(tid):
            return False, '该账号已被学生账号占用'
        salt = secrets.token_hex(8)
        with self._Session() as session:
            session.add(Teacher(id=tid, name=name, role='teacher', salt=salt,
                                password_hash=_hash_pwd(password, salt)))
            session.commit()
        return True, '教师账号已添加'

    def delete_teacher(self, tid: str) -> tuple[bool, str]:
        t = self.find_teacher(tid)
        if t is None:
            return False, '教师账号不存在'
        if self.is_admin(t):
            return False, '不能删除管理员账号'
        with self._Session() as session:
            session.delete(session.get(Teacher, tid))
            session.commit()
        return True, '教师账号已删除'

    def reset_password(self, record: Record, new_pwd: str) -> tuple[bool, str]:
        """重置教师或学生账号密码（按记录中的 id 落库）"""
        if not new_pwd:
            return False, '新密码不能为空'
        salt = secrets.token_hex(8)
        new_hash = _hash_pwd(new_pwd, salt)
        rec_id = record['id']
        with self._Session() as session:
            obj = session.get(Teacher, rec_id) or session.get(Student, rec_id)
            if obj is None:
                return False, '账号不存在'
            obj.salt = salt
            obj.password_hash = new_hash
            session.commit()
        # 同步更新传入的字典视图，保证调用方立即可用
        record['salt'] = salt
        record['password_hash'] = new_hash
        return True, '密码已重置'

    # ---------- 学生修改申请 ----------
    def add_request(self, student: Record, field: str, new_value: str) -> tuple[bool, str]:
        if field not in EDITABLE_FIELDS:
            return False, '该字段不允许修改'
        old_value = student.get(field, '')
        if old_value == new_value:
            return False, '新值与原值相同，无需修改'
        with self._Session() as session:
            req = Request(student_id=student['id'], student_name=student['name'],
                          field=field, field_label=EDITABLE_FIELDS[field],
                          old_value=old_value, new_value=new_value,
                          status='pending',
                          time=time.strftime('%Y-%m-%d %H:%M:%S'))
            session.add(req)
            session.commit()
        return True, '申请已提交，等待管理员审核'

    def list_requests(self, student_id: str | None = None) -> list[dict[str, Any]]:
        with self._Session() as session:
            stmt = select(Request)
            if student_id:
                stmt = stmt.where(Request.student_id == student_id)
            stmt = stmt.order_by(Request.req_id.desc())
            return [_request_dict(r) for r in session.scalars(stmt)]

    def handle_request(self, req_id: int, approve: bool) -> tuple[bool, str]:
        with self._Session() as session:
            r = session.get(Request, req_id)
            if r is None or r.status != 'pending':
                return False, '申请不存在或已处理'
            if approve:
                s = session.get(Student, r.student_id)
                if s is None:
                    return False, '该学生已被删除，无法批准'
                field, label, new_value = r.field, r.field_label, r.new_value
                setattr(s, field, new_value)
                r.status = 'approved'
                session.commit()
                return True, f'已批准修改「{label}」为 {new_value}'
            r.status = 'rejected'
            session.commit()
            return True, '已拒绝该申请'
