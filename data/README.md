# 数据目录说明

## 目录结构

```
data/
├── demo/                           # 演示数据（默认）
│   ├── config.json                # 演示模式配置
│   ├── sessions.json              # 示例会话数据
│   └── sample_observations/       # 示例观测数据
│       └── observations.json      # 预置观测记录
│
├── real_config.json.example       # 真实模式配置模板
├── star_catalogs.db               # 星表数据库
└── sessions.json                  # 运行时会话数据
```

## 使用方式

### 演示模式（默认）
```bash
# 使用演示数据，无需配置API密钥
export DATA_MODE=demo  # 默认已是demo模式
python src/server.py
```

### 真实数据模式
```bash
# 配置环境变量
export DATA_MODE=real
export NASA_ADS_TOKEN=your_token_here
export OPENAI_API_KEY=your_key_here

# 复制配置模板并编辑
cp data/real_config.json.example data/real_config.json
# 编辑 real_config.json 填入你的凭证

python src/server.py
```

## 数据源

| 数据源 | 演示模式 | 真实模式 |
|--------|----------|----------|
| Kepler/TESS | 模拟数据 | NASA Archive |
| 星表 | 示例星表 | 完整星表 |
| 文献 | 示例论文 | arXiv/ADS API |
| 望远镜 | 模拟器 | Seestar S50 |
