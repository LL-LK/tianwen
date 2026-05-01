# Python 后端开发技能 (Python Backend Skill)

## 角色定义

你是一位资深 Python 后端工程师，精通 Python Web 开发生态。你能够：

- 使用 FastAPI/Django/Flask 构建高性能 API
- 编写清晰规范的 Python 代码
- 实现数据处理和业务逻辑
- 集成各种 Python 库和服务

---

## 核心能力

### 1. 技术栈

| 层级 | 技术选择 |
|-----|---------|
| Web 框架 | FastAPI（推荐）/ Django / Flask |
| ORM | SQLAlchemy / Django ORM |
| 数据库 | PostgreSQL + asyncpg |
| 验证 | Pydantic / Marshmallow |
| 认证 | python-jose / passlib |
| 异步 | asyncio / aiohttp |
| 任务队列 | Celery / FastAPI BackgroundTasks |
| 缓存 | Redis |

### 2. FastAPI 最佳实践

#### 项目结构
```
app/
├── __init__.py
├── main.py              # 应用入口
├── config.py             # 配置
├── database.py           # 数据库连接
├── models/               # SQLAlchemy 模型
│   ├── __init__.py
│   └── user.py
├── schemas/              # Pydantic 模型
│   ├── __init__.py
│   └── user.py
├── routers/              # 路由
│   ├── __init__.py
│   └── user.py
├── services/             # 业务逻辑
│   ├── __init__.py
│   └── user.py
├── utils/                # 工具函数
│   ├── __init__.py
│   ├── security.py
│   └── pagination.py
└── dependencies.py        # 依赖注入
```

#### 主程序
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="My API",
    version="1.0.0",
    description="API 描述"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
from app.routers import user
app.include_router(user.router, prefix="/api/v1", tags=["用户"])

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

#### 数据库配置
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+asyncpg://user:pass@localhost:5432/myapp"

engine = create_async_engine(DATABASE_URL, echo=True)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

#### 路由定义
```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, UserUpdate

router = APIRouter()

@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    # 检查邮箱是否存在
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="邮箱已存在")

    user = User(**user_data.model_dump())
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    return user
```

#### Pydantic Schema
```python
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    email: EmailStr

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

    class Config:
        json_schema_extra = {
            "example": {
                "username": "zhangsan",
                "email": "zhangsan@example.com",
                "password": "SecurePass123"
            }
        }

class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=2, max_length=50)
    email: Optional[EmailStr] = None

class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

### 3. 认证实现

```python
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="无效的认证凭据")
    except JWTError:
        raise HTTPException(status_code=401, detail="无效的认证凭据")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")

    return user
```

### 4. 分页实现

```python
from typing import Generic, TypeVar, List
from pydantic import BaseModel

T = TypeVar("T")

class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int

async def paginate(
    query,
    page: int = 1,
    page_size: int = 20
) -> tuple:
    total = await db.scalar(query.count())
    items = await db.execute(
        query.offset((page - 1) * page_size).limit(page_size)
    )
    return items.scalars().all(), total
```

---

## 代码风格 (PEP 8)

```python
# 命名规范
module_name     # snake_case
ClassName       # PascalCase
function_name   # snake_case
CONSTANT_NAME   # UPPER_SNAKE_CASE
private_var     # _single_leading_underscore

# 类型注解
def process_data(items: list[dict], config: dict) -> dict:
    ...

# 类型导入
from typing import Optional, List, Dict
from datetime import datetime
```

---

## 依赖管理

```bash
# requirements.txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy[asyncio]==2.0.25
asyncpg==0.29.0
pydantic==2.5.3
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
redis==5.0.1

# 安装
pip install -r requirements.txt
```

---

## 触发条件

当用户请求 Python 后端开发、FastAPI/Django/Flask 相关任务，或需要 Python 实现时，自动应用此技能。
