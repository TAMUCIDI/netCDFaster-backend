FROM python:3.9-slim

RUN mkdir -p /app/tmp && chmod 777 /app/tmp

WORKDIR /

# 安装系统依赖（根据实际需要补充）
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY .env .
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn
RUN pip install netCDF4
# 复制应用代码和配置文件
COPY . .

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "wsgi:application"]