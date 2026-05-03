# 天问-AGI 架构重构计划 v1.0

## 执行时间
2026-05-03

## 一、目标

### 1.1 3-Agent架构简化 (从4-Agent)

| 新Agent | 英文名 | 职责 | 整合模块 |
|---------|--------|------|----------|
| M1: 数据挖掘Agent | DataMiningAgent | 文献调研、数据分析、模式发现 | literature_researcher.py, data_miner.py |
| M2: 观测指导Agent | ObservationGuidanceAgent | 假说生成、调度规划、观测指导 | hypothesis_generator.py, observation_scheduler.py |
| M3: 观测执行Agent | ObservationExecutionAgent | 望远镜控制、数据采集、执行反馈 | observation_executor.py, observatory_linker.py |

### 1.2 Chain of Draft集成

已在 `reasoning_engine.py` 中实现:
- `ChainOfDraftAdapter` 类 (502-564行)
- `_think_cod()` 方法 (897-949行)
- token消耗降低60-80%

### 1.3 情景记忆系统

"情景-情感-意图"三位一体记忆:
- 区别于现有的持久化(vector_memory)和向量记忆(vector_rag)
- 新模块: `scenario_memory.py`

### 1.4 梦引擎实现

离线整合机制，自动发现隐藏模式:
- 新模块: `dream_engine.py`

## 二、执行计划

### 阶段1: 备份 (已完成)
- 创建备份目录

### 阶段2: 代码重构
1. 创建3-Agent基础架构
2. 整合现有模块到3-Agent
3. 清理冗余代码

### 阶段3: Chain of Draft验证

### 阶段4: 新功能实现
- 情景记忆系统
- 梦引擎

## 三、关键文件

| 文件 | 行数 | 状态 | 说明 |
|------|------|------|------|
| multi_agent_coordinator.py | 2344 | 待简化 | 4-Agent协调器 |
| literature_researcher.py | 2257 | M1 | 文献研究 |
| data_miner.py | 1578 | M1 | 数据挖掘 |
| hypothesis_generator.py | ~300 | M2 | 假说生成 |
| observation_scheduler.py | ~560 | M2 | 调度规划 |
| observation_executor.py | 747 | M3 | 观测执行 |
| observatory_linker.py | 1625 | M3 | 望远镜链接 |
| reasoning_engine.py | 1185 | CoD | 已实现Chain of Draft |

## 四、验收标准

1. 3-Agent架构运行正常
2. Chain of Draft token消耗降低60-80%
3. 情景记忆系统可正常工作
4. 梦引擎可发现隐藏模式
