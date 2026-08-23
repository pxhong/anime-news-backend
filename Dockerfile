FROM python:3.10-slim

# 安装 ffmpeg（构建时永久装进镜像，之后每次部署都有）
RUN apt-get update \
    && apt-get install -y ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080

CMD ["gunicorn", "DjangoProject.wsgi:application", "--bind", "0.0.0.0:8080", "--timeout", "300", "--workers", "2"]