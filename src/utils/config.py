"""
生产环境配置 - Neo4j + ChromaDB
天问-AGI v3.4.0

使用方法:
    from src.utils.config import get_config, ProductionConfig, DevelopmentConfig

    # 开发环境
    config = DevelopmentConfig()

    # 生产环境
    config = ProductionConfig()
"""

import os
from typing import Optional


class BaseConfig:
    """基础配置类"""

    # Neo4j 图数据库
    neo4j_uri: Optional[str] = None
    neo4j_auth: Optional[tuple] = None
    neo4j_database: str = "neo4j"

    # ChromaDB 向量数据库
    chroma_persist_dir: Optional[str] = None
    chroma_collection_name: str = "tianwen_papers"

    # Redis 缓存 (可选)
    redis_url: Optional[str] = None

    # 日志级别
    log_level: str = "INFO"

    @classmethod
    def get_neo4j_config(cls) -> dict:
        """获取Neo4j配置"""
        return {
            "uri": cls.neo4j_uri,
            "auth": cls.neo4j_auth,
            "database": cls.neo4j_database,
        }

    @classmethod
    def get_chroma_config(cls) -> dict:
        """获取ChromaDB配置"""
        return {
            "persist_directory": cls.chroma_persist_dir,
            "collection_name": cls.chroma_collection_name,
        }


class DevelopmentConfig(BaseConfig):
    """
    开发环境配置 - 使用内存模式

    特点:
    - Neo4j: 内存模式，无需外部依赖
    - ChromaDB: 内存模式，快速启动
    - 适合本地开发和测试
    """

    # 开发模式使用内存存储
    neo4j_uri = None  # 内存模式
    chroma_persist_dir = None  # 内存模式

    # 开发环境日志
    log_level = "DEBUG"

    # 开发环境API Key (如果需要)
    openai_api_key = os.environ.get("OPENAI_API_KEY", "")
    anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")


class ProductionConfig(BaseConfig):
    """
    生产环境配置 - 使用持久化存储

    特点:
    - Neo4j: 持久化图数据库，完整图查询能力
    - ChromaDB: 持久化向量存储，支持大规模语义检索
    - 推荐使用Docker Compose部署
    """

    # Neo4j 配置 (生产环境)
    neo4j_uri = os.environ.get("NEO4J_URI", "bolt://neo4j:7687")
    neo4j_auth = (
        os.environ.get("NEO4J_USER", "neo4j"),
        os.environ.get("NEO4J_PASSWORD", "password"),
    )
    neo4j_database = "neo4j"

    # ChromaDB 配置 (生产环境)
    chroma_persist_dir = os.environ.get("CHROMA_PERSIST_DIR", "/data/chroma")
    chroma_collection_name = "tianwen_papers"

    # Redis 缓存 (生产环境，推荐)
    redis_url = os.environ.get("REDIS_URL", "redis://redis:6379")

    # 生产环境日志
    log_level = "INFO"

    # 生产环境API Key (必需)
    openai_api_key = os.environ.get("OPENAI_API_KEY", "")
    anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")


class DockerComposeConfig:
    """
    Docker Compose 配置模板

    使用方式:
        docker-compose up -d
    """

    DOCKER_COMPOSE = """version: '3.8'

services:
  # Neo4j 图数据库
  neo4j:
    image: neo4j:5
    ports:
      - "7474:7474"  # Neo4j Browser
      - "7687:7687"  # Bolt Protocol
    environment:
      - NEO4J_AUTH=neo4j/password
      - NEO4J_PLUGINS=["apoc"]
      - NEO4J_dbms_memory_heap_initial__size=512m
      - NEO4J_dbms_memory_heap_max__size=2g
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "wget -q --spider localhost:7474 || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 5

  # ChromaDB 向量数据库
  chromadb:
    image: chromadb/chroma:latest
    ports:
      - "8000:8000"
    volumes:
      - chroma_data:/data/chroma
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8000/api/v1/heartbeat || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 5

  # Redis 缓存 (可选)
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    command: redis-server --appendonly yes

  # 天问-AGI 后端
  tianwen-api:
    build: .
    ports:
      - "5000:5000"
    environment:
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=password
      - CHROMA_PERSIST_DIR=/data/chroma
      - REDIS_URL=redis://redis:6379
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    depends_on:
      neo4j:
        condition: service_healthy
      chromadb:
        condition: service_healthy
      redis:
        condition: service_started
    restart: unless-stopped

volumes:
  neo4j_data:
  neo4j_logs:
  chroma_data:
  redis_data:
"""

    @classmethod
    def save_docker_compose(cls, path: str = "docker-compose.yml"):
        """保存Docker Compose文件"""
        with open(path, 'w', encoding='utf-8') as f:
            f.write(cls.DOCKER_COMPOSE)
        print(f"✅ Docker Compose配置已保存到: {path}")
        print("   使用命令启动: docker-compose up -d")


def get_config() -> BaseConfig:
    """
    根据环境自动选择配置

    Returns:
        BaseConfig: 开发或生产配置
    """
    env = os.environ.get("TIANWEN_ENV", "development")

    if env.lower() in ("production", "prod"):
        return ProductionConfig()
    else:
        return DevelopmentConfig()


# 便捷函数
def print_config_summary():
    """打印配置摘要"""
    config = get_config()
    config_type = type(config).__name__

    print("=" * 50)
    print(f"天问-AGI 配置 ({config_type})")
    print("=" * 50)
    print(f"Neo4j URI: {config.neo4j_uri or '内存模式'}")
    print(f"ChromaDB: {config.chroma_persist_dir or '内存模式'}")
    print(f"日志级别: {config.log_level}")
    print("=" * 50)


if __name__ == "__main__":
    print_config_summary()
    print("\n生成Docker Compose配置:")
    print(DockerComposeConfig.DOCKER_COMPOSE[:500] + "...")
