# -*- coding: utf-8 -*-
"""学生管理系统 - FastAPI 后端（第二阶段：API 服务）

运行：
    python -m uvicorn main:app --reload
启动后：
    前端页面: http://127.0.0.1:8000/
    接口文档: http://127.0.0.1:8000/docs（Swagger，可直接测试接口）

约定：
    - 所有接口统一返回 {"code": 200, "msg": "...", "data": ...}
    - 登录成功后返回 token，后续请求携带 Header: Authorization: Bearer <token>
    - 业务层完全复用 database.py（零 UI 依赖），本文件只做协议转换与鉴权
"""
import base64
import hashlib
import hmac
import json
import os
import time
from pathlib import Path
from typing import Annotated, Any, Literal

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from database import Database, EDITABLE_FIELDS

# 加载项目根目录的 .env 配置文件（敏感密钥不写在代码里）
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

db = Database()

# ==================== 应用与统一响应 ====================

app = FastAPI(title="学生管理系统 API", description="由 Tkinter 桌面版重构而来")

# 开发阶段允许跨域（例如用 Live Server 的 5500 端口打开前端时）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def _no_cache_static(request: Request, call_next):
    """开发阶段：静态资源一律禁用浏览器缓存，改完代码刷新即生效"""
    response = await call_next(request)
    path = request.url.path
    if not path.startswith("/api") and not path.startswith("/docs") \
            and not path.startswith("/openapi"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
    return response


def ok(data: Any = None, msg: str = "success") -> dict:
    return {"code": 200, "msg": msg, "data": data}


def fail(code: int, msg: str) -> JSONResponse:
    """业务失败：HTTP 仍返回 200，用 code 区分"""
    return JSONResponse({"code": code, "msg": msg, "data": None})


@app.exception_handler(HTTPException)
async def _http_exception(_: Request, exc: HTTPException) -> JSONResponse:
    """401 / 403 / 404 等也统一成相同 JSON 结构"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "msg": str(exc.detail), "data": None},
    )


# ==================== Token（简化 HMAC 签名，后续可换标准 JWT） ====================

# 签名密钥从 .env 的 SECRET 读取；缺失时用开发用默认值（部署前必须配置）
SECRET = os.environ.get("SECRET", "dev-secret-change-me")
TOKEN_TTL = 8 * 3600              # 有效期 8 小时


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def create_token(payload: dict) -> str:
    body = _b64(json.dumps({**payload, "exp": int(time.time()) + TOKEN_TTL},
                           separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    sig = hmac.new(SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def parse_token(token: str) -> dict | None:
    try:
        body, sig = token.split(".")
    except ValueError:
        return None
    expect = hmac.new(SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expect, sig):
        return None
    try:
        payload = json.loads(_unb64(body))
    except (ValueError, UnicodeDecodeError):
        return None
    if payload.get("exp", 0) < time.time():
        return None
    return payload


def current_user(authorization: str = Header(default="")) -> dict:
    token = authorization.removeprefix("Bearer ").strip() if authorization else ""
    payload = parse_token(token) if token else None
    if payload is None:
        raise HTTPException(status_code=401, detail="未登录或登录已过期")
    return payload  # {uid, name, role, exp}


def require_admin(user: dict = Depends(current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


# ==================== 请求体模型（后端严格校验） ====================

class LoginBody(BaseModel):
    username: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=64)
    role: Literal["teacher", "student"]


class StudentCreate(BaseModel):
    id: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=20)
    gender: Literal["男", "女"] = "男"
    class_name: str = Field(default="", max_length=32)
    phone: str = Field(default="", max_length=20)
    password: str = Field(min_length=4, max_length=64)


class StudentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=20)
    gender: Literal["男", "女"] | None = None
    class_name: str | None = Field(default=None, max_length=32)
    phone: str | None = Field(default=None, max_length=20)


Score = Annotated[int, Field(ge=0, le=100)]


class GradesBody(BaseModel):
    grades: dict[str, Score]


def _safe_student(s: dict) -> dict:
    """返回给前端的学生信息（剔除 salt / password_hash）"""
    grades = s.get("grades", {})
    return {
        "id": s["id"], "name": s["name"], "gender": s["gender"],
        "class_name": s["class_name"], "phone": s["phone"],
        "grades": grades, "total": sum(grades.values()),
    }


# ==================== 接口 ====================

@app.post("/api/login")
def login(body: LoginBody):
    username = body.username.strip()
    if body.role == "teacher":
        rec, err = db.teacher_login(username, body.password)
        role = ("admin" if db.is_admin(rec) else "teacher") if rec else "teacher"
    else:
        rec, err = db.student_login(username, body.password)
        role = "student"
    if err or rec is None:
        return fail(400, err or "登录失败")
    token = create_token({"uid": rec["id"], "name": rec["name"], "role": role})
    return ok({"token": token,
               "user": {"id": rec["id"], "name": rec["name"], "role": role}},
              "登录成功")


@app.get("/api/me")
def me(user: dict = Depends(current_user)):
    if user["role"] == "student":
        s = db.find_student(user["uid"])
        if s is None:
            raise HTTPException(404, "账号不存在")
        return ok(_safe_student(s))
    t = db.find_teacher(user["uid"])
    if t is None:
        raise HTTPException(404, "账号不存在")
    return ok({"id": t["id"], "name": t["name"], "role": user["role"]})


@app.get("/api/students")
def list_students(keyword: str = "", user: dict = Depends(current_user)):
    if user["role"] not in ("admin", "teacher"):
        raise HTTPException(403, "学生只能查看自己的信息")
    kw = keyword.strip().lower()
    rows = [_safe_student(s) for s in db.data["students"]
            if not kw or kw in (s["id"] + s["name"] + s["class_name"]).lower()]
    return ok(rows)


@app.get("/api/students/{sid}")
def get_student(sid: str, user: dict = Depends(current_user)):
    if user["role"] == "student" and user["uid"] != sid:
        raise HTTPException(403, "只能查看自己的信息")
    s = db.find_student(sid)
    if s is None:
        raise HTTPException(404, "学生不存在")
    return ok(_safe_student(s))


@app.post("/api/students")
def add_student(body: StudentCreate, _: dict = Depends(require_admin)):
    success, msg = db.add_student(body.id.strip(), body.name.strip(), body.gender,
                                  body.class_name.strip(), body.phone.strip(),
                                  body.password)
    return ok(msg=msg) if success else fail(400, msg)


@app.put("/api/students/{sid}")
def update_student(sid: str, body: StudentUpdate, _: dict = Depends(require_admin)):
    success, msg = db.update_student_info(sid, name=body.name, gender=body.gender,
                                          class_name=body.class_name, phone=body.phone)
    return ok(msg=msg) if success else fail(404, msg)


@app.delete("/api/students/{sid}")
def delete_student(sid: str, _: dict = Depends(require_admin)):
    success, msg = db.delete_student(sid)
    return ok(msg=msg) if success else fail(404, msg)


@app.put("/api/students/{sid}/grades")
def set_grades(sid: str, body: GradesBody, _: dict = Depends(require_admin)):
    success, msg = db.set_grades(sid, body.grades)
    return ok(msg=msg) if success else fail(400, msg)


# ==================== 密码管理 ====================

class PasswordChange(BaseModel):
    old_password: str = Field(min_length=1, max_length=64)
    new_password: str = Field(min_length=4, max_length=64)


@app.put("/api/me/password")
def change_my_password(body: PasswordChange, user: dict = Depends(current_user)):
    """修改自己的密码：先校验旧密码"""
    if user["role"] == "student":
        rec = db.find_student(user["uid"])
    else:
        rec = db.find_teacher(user["uid"])
    if rec is None:
        raise HTTPException(404, "账号不存在")
    if not db.verify(rec, body.old_password):
        return fail(400, "旧密码不正确")
    if body.old_password == body.new_password:
        return fail(400, "新密码不能与旧密码相同")
    success, msg = db.reset_password(rec, body.new_password)
    return ok(msg=msg) if success else fail(400, msg)


class ResetPasswordBody(BaseModel):
    target_id: str = Field(min_length=1, max_length=20)
    new_password: str = Field(min_length=4, max_length=64)


@app.post("/api/passwords/reset")
def reset_password_api(body: ResetPasswordBody, _: dict = Depends(require_admin)):
    """管理员重置他人密码（教师或学生账号均可）"""
    target = body.target_id.strip()
    rec = db.find_teacher(target) or db.find_student(target)
    if rec is None:
        return fail(404, "账号不存在")
    success, msg = db.reset_password(rec, body.new_password)
    return ok(msg=msg) if success else fail(400, msg)


# ==================== 教师账号管理（仅管理员） ====================

class TeacherCreate(BaseModel):
    id: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=20)
    password: str = Field(min_length=4, max_length=64)


@app.get("/api/teachers")
def list_teachers(_: dict = Depends(require_admin)):
    rows = [{"id": t["id"], "name": t["name"], "role": t["role"]}
            for t in db.data["teachers"]]
    return ok(rows)


@app.post("/api/teachers")
def add_teacher(body: TeacherCreate, _: dict = Depends(require_admin)):
    success, msg = db.add_teacher(body.id.strip(), body.name.strip(), body.password)
    return ok(msg=msg) if success else fail(400, msg)


@app.delete("/api/teachers/{tid}")
def delete_teacher(tid: str, user: dict = Depends(require_admin)):
    if tid == user["uid"]:
        return fail(400, "不能删除当前登录的账号")
    success, msg = db.delete_teacher(tid)
    return ok(msg=msg) if success else fail(400, msg)


# ==================== 学生修改申请 ====================

class RequestCreate(BaseModel):
    field: str = Field(min_length=1, max_length=20)
    new_value: str = Field(min_length=1, max_length=50)


@app.get("/api/editable-fields")
def editable_fields(_: dict = Depends(current_user)):
    """学生可申请修改的字段（key -> 中文名）"""
    return ok(EDITABLE_FIELDS)


@app.post("/api/requests")
def add_request(body: RequestCreate, user: dict = Depends(current_user)):
    if user["role"] != "student":
        raise HTTPException(403, "只有学生可以提交修改申请")
    s = db.find_student(user["uid"])
    if s is None:
        raise HTTPException(404, "学生不存在")
    success, msg = db.add_request(s, body.field.strip(), body.new_value.strip())
    return ok(msg=msg) if success else fail(400, msg)


@app.get("/api/requests")
def list_requests(user: dict = Depends(current_user)):
    if user["role"] == "admin":
        return ok(db.list_requests())
    if user["role"] == "student":
        return ok(db.list_requests(user["uid"]))
    raise HTTPException(403, "普通教师无权查看修改申请")


class RequestHandle(BaseModel):
    approve: bool


@app.post("/api/requests/{req_id}/handle")
def handle_request(req_id: int, body: RequestHandle, _: dict = Depends(require_admin)):
    success, msg = db.handle_request(req_id, body.approve)
    return ok(msg=msg) if success else fail(400, msg)


# ==================== 数据统计 ====================

@app.get("/api/stats")
def stats(user: dict = Depends(current_user)):
    """班级人数分布、各科平均分等统计（教师/管理员可见）"""
    if user["role"] == "student":
        raise HTTPException(403, "学生不能查看全班统计")
    students = db.data["students"]
    classes: dict[str, int] = {}
    for s in students:
        key = s["class_name"] or "未分班"
        classes[key] = classes.get(key, 0) + 1
    subject_scores: dict[str, list[int]] = {}
    for s in students:
        for sub, score in s.get("grades", {}).items():
            subject_scores.setdefault(sub, []).append(score)
    return ok({
        "student_count": len(students),
        "teacher_count": len(db.data["teachers"]),
        "pending_requests": sum(1 for r in db.data["requests"]
                                if r["status"] == "pending"),
        "classes": sorted(({"name": k, "count": v} for k, v in classes.items()),
                          key=lambda x: (-x["count"], x["name"])),
        "subject_avg": sorted(({"subject": sub,
                                "avg": round(sum(v) / len(v), 1),
                                "count": len(v)}
                               for sub, v in subject_scores.items()),
                              key=lambda x: x["subject"]),
    })


# ==================== 静态前端（最后挂载，不遮挡 API 路由） ====================

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
