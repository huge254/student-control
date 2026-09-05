# 学生管理系统（Web 版）

由 tkinter 桌面版改造而来的前后端分离 Web 系统。

## 技术栈

- 后端：FastAPI + SQLAlchemy（MySQL）
- 前端：原生 HTML / CSS / JavaScript（无框架）
- 部署：Docker Compose（后端 + MySQL + Nginx 三容器）

## 功能

- 教师 / 学生 / 管理员三种角色，Token 登录鉴权
- 学生信息增删改查、成绩管理、关键词搜索、导出 CSV
- 教师账号管理（添加 / 删除 / 重置密码）
- 学生提交信息修改申请，管理员审核后生效
- 数据统计（班级人数分布、各科平均分）
- 修改密码（校验旧密码）

## 快速开始

```bash
pip install -r requirements.txt
# 复制配置模板并填入真实的数据库密码与密钥
copy .env.example .env
python -m uvicorn main:app --reload
```

浏览器访问 `http://127.0.0.1:8000/`

默认账号：管理员 `admin / admin123`，教师 `t001 / 123456`，学生 `2024001 / 123456`

## Docker 部署

```bash
docker compose up -d --build
```

访问 `http://127.0.0.1/`（Nginx 对外 80 端口）

## 接口文档

启动后访问 `http://127.0.0.1:8000/docs`（Swagger）

## 测试

```bash
python test_api.py
```
