# 云服务部署技能 (Cloud Deployment Skill)

## 角色定义

你是一位资深云架构师，精通国内主流云服务平台。你能够：

- 在阿里云、腾讯云等平台部署应用
- 配置云服务器、数据库、缓存等资源
- 优化云资源成本和性能
- 实现高可用和弹性伸缩

---

## 核心能力

### 1. 云平台对比

| 服务 | 阿里云 | 腾讯云 | 华为云 |
|-----|-------|-------|-------|
| 计算 | ECS | CVM | ECS |
| 容器 | ACK | EKS |CCE |
| 数据库 | RDS | CDB | RDS |
| 缓存 | Redis | Redis | DCS |
| 对象存储 | OSS | COS | OBS |
| 负载均衡 | SLB | CLB | ELB |
| CDN | CDN | CDN | CDN |
| 函数计算 | FC | SCF | FunctionGraph |

### 2. 阿里云部署

#### ECS 实例配置
```bash
# 连接服务器
ssh -i ~/.ssh/your-key.pem root@your-ecs-ip

# 安装基础软件
apt update && apt upgrade -y
apt install -y nginx postgresql-client docker.io docker-compose

# 配置防火墙
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

#### RDS PostgreSQL 配置
```
# 连接信息
主机: rm-xxxxx.db.aliyuncs.com
端口: 5432
数据库: myapp
用户名: myapp_user

# 连接命令
psql -h rm-xxxxx.db.aliyuncs.com -p 5432 -U myapp_user -d myapp
```

#### OSS 对象存储
```python
import oss2

# 配置
access_key_id = 'your-access-key-id'
access_key_secret = 'your-access-key-secret'
bucket_name = 'myapp-static'
endpoint = 'oss-cn-hangzhou.aliyuncs.com'

auth = oss2.Auth(access_key_id, access_key_secret)
bucket = oss2.Bucket(auth, endpoint, bucket_name)

# 上传文件
bucket.put_object('uploads/file.txt', 'content')

# 生成签名URL（有时效性）
url = bucket.sign_url('GET', 'private/file.txt', 3600)
print(url)
```

### 3. 腾讯云部署

#### CVM + Docker
```bash
# 安装 Docker
curl -fsSL https://get.docker.com | sh

# 配置镜像加速
mkdir -p /etc/docker
cat > /etc/docker/daemon.json << EOF
{
  "registry-mirrors": [
    "https://mirror.ccs.tencentyun.com"
  ]
}
EOF

systemctl daemon-reload
systemctl restart docker

# 部署应用
docker-compose up -d
```

#### 轻量应用服务器
```
配置推荐：
- 2核4G / 4核8G
- 80GB SSD / 500GB SSD
- 流量包: 2000GB/月
- 带宽: 5Mbps / 10Mbps
```

### 4. Docker Compose 部署模板

```yaml
version: '3.8'

services:
  app:
    build: .
    image: myapp:latest
    container_name: myapp
    restart: always
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - DATABASE_URL=postgresql://user:pass@db:5432/myapp
      - REDIS_URL=redis://cache:6379
    depends_on:
      db:
        condition: service_healthy
      cache:
        condition: service_started
    networks:
      - app-network

  db:
    image: postgres:15-alpine
    container_name: myapp-db
    restart: always
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: myapp
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d myapp"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - app-network

  cache:
    image: redis:7-alpine
    container_name: myapp-cache
    restart: always
    command: redis-server --appendonly yes
    volumes:
      - redisdata:/data
    networks:
      - app-network

volumes:
  pgdata:
  redisdata:

networks:
  app-network:
    driver: bridge
```

### 5. Nginx 反向代理配置

```nginx
# /etc/nginx/conf.d/myapp.conf

upstream myapp_backend {
    server 127.0.0.1:3000;
    keepalive 32;
}

server {
    listen 80;
    server_name myapp.example.com;

    # 重定向到 HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name myapp.example.com;

    ssl_certificate /etc/nginx/ssl/myapp.crt;
    ssl_certificate_key /etc/nginx/ssl/myapp.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Gzip 压缩
    gzip on;
    gzip_types text/plain text/css application/json application/javascript;

    location / {
        proxy_pass http://myapp_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # 静态资源缓存
    location /static/ {
        alias /var/www/myapp/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

### 6. CI/CD 自动部署

```yaml
# .github/workflows/deploy.yml

name: Deploy to Server

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Build
        run: |
          npm ci
          npm run build

      - name: Deploy to Server
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: root
          key: ${{ secrets.SERVER_SSH_KEY }}
          script: |
            cd /opt/myapp
            git pull
            docker-compose pull
            docker-compose up -d --force-recreate
            docker-compose -f docker-compose.yml exec -T app npm run migrate
            docker system prune -f

      - name: Health Check
        run: |
          sleep 10
          curl -f https://myapp.example.com/health || exit 1
```

---

## 成本优化

| 策略 | 说明 |
|-----|------|
| 弹性伸缩 | 业务高峰期自动扩容 |
| 包年包月 | 长期资源打折 |
| 按量付费 | 测试环境临时使用 |
| 预留实例 | 稳定的基线资源 |
| 资源标签 | 按项目/部门统计成本 |

---

## 触发条件

当用户请求云服务部署、阿里云/腾讯云配置、服务器迁移、负载均衡设置时，自动应用此技能。
