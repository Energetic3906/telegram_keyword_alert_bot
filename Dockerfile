# 使用官方Python基础镜像
FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 安装编译所需的系统依赖 (regex 库可能需要 gcc)
# 安装后清理缓存以减小镜像体积
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libc6-dev && \
    rm -rf /var/lib/apt/lists/*

# 1. 先只复制 requirements.txt
# 这样做利用了 Docker 缓存层：只要依赖不变，就不会重新下载安装包
COPY requirements.txt .

# 2. 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 3. 最后复制项目所有文件
COPY . .

# 设置启动命令 (不再需要 pipenv run)
CMD ["python", "main.py"]