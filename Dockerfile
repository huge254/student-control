# 学生管理系统 - 后端镜像（生产方式运行：无 --reload，监听容器内所有网卡）
FROM python:3.13-slim

WORKDIR /app

# 先复制依赖清单，利用 Docker 构建缓存
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码（静态文件由 Nginx 容器提供，进镜像是为保证后端挂载目录存在）
COPY main.py database.py models.py ./
COPY static ./static

EXPOSE 8000

# 生产运行：uvicorn 直接启动，不带 --reload
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
