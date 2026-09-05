# -*- coding: utf-8 -*-
"""学生管理系统 - 数据模型（SQLAlchemy ORM，MySQL）

表结构：
  teachers  教师账号（含加盐密码哈希）
  students  学生账号（含加盐密码哈希）
  grades    学生成绩（一个学生多条记录：科目 + 分数）
  requests  学生修改申请（含审核状态）
"""
from sqlalchemy import (Boolean, Column, ForeignKey, Integer, String,
                        UniqueConstraint)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Teacher(Base):
    __tablename__ = "teachers"
    id = Column(String(20), primary_key=True)          # 工号
    name = Column(String(20), nullable=False)
    role = Column(String(10), nullable=False, default="teacher")  # admin / teacher
    salt = Column(String(32), nullable=False)
    password_hash = Column(String(128), nullable=False)


class Student(Base):
    __tablename__ = "students"
    id = Column(String(20), primary_key=True)          # 学号
    name = Column(String(20), nullable=False)
    gender = Column(String(4), nullable=False, default="男")
    class_name = Column(String(32), nullable=False, default="")
    phone = Column(String(20), nullable=False, default="")
    salt = Column(String(32), nullable=False)
    password_hash = Column(String(128), nullable=False)
    grades = relationship("Grade", back_populates="student",
                          cascade="all, delete-orphan", lazy="selectin")


class Grade(Base):
    """成绩拆为独立表（原来是学生记录里的字典）"""
    __tablename__ = "grades"
    student_id = Column(String(20), ForeignKey("students.id", ondelete="CASCADE"),
                        primary_key=True)
    subject = Column(String(30), primary_key=True)     # 科目名
    score = Column(Integer, nullable=False)
    student = relationship("Student", back_populates="grades")
    __table_args__ = (UniqueConstraint("student_id", "subject", name="uq_grade"),)


class Request(Base):
    __tablename__ = "requests"
    req_id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String(20), nullable=False)
    student_name = Column(String(20), nullable=False)
    field = Column(String(20), nullable=False)         # phone / gender / class_name / name
    field_label = Column(String(20), nullable=False)   # 中文字段名
    old_value = Column(String(50), nullable=False, default="")
    new_value = Column(String(50), nullable=False)
    status = Column(String(10), nullable=False, default="pending")  # pending/approved/rejected
    time = Column(String(19), nullable=False)          # YYYY-MM-DD HH:MM:SS
