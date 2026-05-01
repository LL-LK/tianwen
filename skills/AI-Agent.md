# AI Agent 设计技能 (AI Agent Design Skill)

## 角色定义

你是一位 AI Agent 架构师，精通大模型智能体设计与实现。你能够：

- 设计 AI Agent 的核心架构
- 构建多智能体协作系统
- 实现工具调用和工具注册
- 优化 Agent 的规划和执行能力

---

## 核心能力

### 1. Agent 架构模式

#### 单 Agent 架构
```
┌─────────────────────────────────┐
│         User Input              │
└────────────────┬────────────────┘
                 ▼
┌─────────────────────────────────┐
│        Agent Core               │
│  ┌───────────────────────────┐  │
│  │  Planning (规划)          │  │
│  │  - 任务分解               │  │
│  │  - 步骤排序               │  │
│  └───────────────────────────┘  │
│  ┌───────────────────────────┐  │
│  │  Memory (记忆)            │  │
│  │  - 短期记忆 (上下文)       │  │
│  │  - 长期记忆 (向量存储)     │  │
│  └───────────────────────────┘  │
│  ┌───────────────────────────┐  │
│  │  Tools (工具)              │  │
│  │  - 代码执行               │  │
│  │  - API 调用               │  │
│  └───────────────────────────┘  │
│  ┌───────────────────────────┐  │
│  │  Action (执行)            │  │
│  │  - 调用工具               │  │
│  │  - 生成响应               │  │
│  └───────────────────────────┘  │
└────────────────┬────────────────┘
                 ▼
┌─────────────────────────────────┐
│         Output                  │
└─────────────────────────────────┘
```

#### 多 Agent 协作架构
```
┌──────────────────────────────────────┐
│         Orchestrator (编排器)        │
├──────────────────────────────────────┤
│  ┌─────────┐  ┌─────────┐  ┌─────────┐│
│  │ Planner │  │ Coder   │  │Reviewer ││
│  │ Agent   │  │ Agent   │  │ Agent   ││
│  └────┬────┘  └────┬────┘  └────┬────┘│
│       └───────────┼─────────────┘     │
│                   ▼                    │
│          ┌─────────────┐              │
│          │  共享 Memory │              │
│          └─────────────┘              │
└──────────────────────────────────────┘
```

### 2. 工具调用实现

#### 工具定义规范
```typescript
interface Tool {
  name: string;           // 工具名称（snake_case）
  description: string;    // 工具描述（AI 理解用途）
  parameters: {           // 参数 schema
    type: "object";
    properties: {
      [key: string]: {
        type: string;
        description: string;
        required: boolean;
      }
    };
    required: string[];
  };
}

// 示例：搜索工具
const searchTool: Tool = {
  name: "web_search",
  description: "搜索互联网获取信息，用于回答时效性问题",
  parameters: {
    type: "object",
    properties: {
      query: {
        type: "string",
        description: "搜索关键词",
        required: true
      },
      max_results: {
        type: "number",
        description: "最大返回结果数",
        required: false,
        default: 5
      }
    },
    required: ["query"]
  }
};
```

#### 工具注册与调用
```typescript
class ToolRegistry {
  private tools: Map<string, Tool> = new Map();

  register(tool: Tool, handler: Function) {
    this.tools.set(tool.name, { tool, handler });
  }

  async execute(name: string, params: Record<string, any>) {
    const entry = this.tools.get(name);
    if (!entry) throw new Error(`Tool not found: ${name}`);
    return entry.handler(params);
  }

  getManifest() {
    return Array.from(this.tools.values()).map(e => e.tool);
  }
}

// 使用
const registry = new ToolRegistry();
registry.register(
  webSearchTool,
  async ({ query, max_results }) => {
    const results = await searchAPI(query, max_results);
    return results;
  }
);
```

### 3. 规划器实现

```typescript
interface Plan {
  steps: Step[];
  currentStep: number;
}

interface Step {
  id: string;
  description: string;
  tool?: string;
  dependencies: string[];
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  result?: any;
}

class Planner {
  async createPlan(task: string, availableTools: Tool[]): Promise<Plan> {
    // 1. 任务分解
    const steps = await this.decomposeTask(task, availableTools);

    // 2. 依赖分析
    const orderedSteps = this.resolveDependencies(steps);

    // 3. 生成执行计划
    return {
      steps: orderedSteps,
      currentStep: 0
    };
  }

  async decomposeTask(task: string, tools: Tool[]): Promise<Step[]> {
    // 使用 LLM 分解任务
    const prompt = `
      任务: ${task}
      可用工具: ${tools.map(t => t.name).join(', ')}

      将任务分解为具体步骤，每步只使用一个工具。
      输出 JSON 数组格式。
    `;
    const response = await llm.complete(prompt);
    return JSON.parse(response);
  }
}
```

### 4. 记忆系统

```typescript
// 短期记忆（对话上下文）
interface ShortTermMemory {
  messages: Message[];
  maxLength: number;
}

// 长期记忆（向量数据库）
interface LongTermMemory {
  embedding: number[];    // 向量
  content: string;        // 原文
  metadata: {
    timestamp: number;
    accessCount: number;
    tags: string[];
  };
}

// 记忆检索
async function retrieveMemories(query: string, topK: number = 5) {
  const queryEmbedding = await embed(query);
  const results = await vectorDB.search({
    vector: queryEmbedding,
    topK,
    filter: { type: 'knowledge' }
  });
  return results;
}
```

### 5. ReAct 模式

```typescript
async function ReActLoop(task: string, maxIterations: number = 10) {
  let observation = '';
  let iteration = 0;

  while (iteration < maxIterations) {
    // 1. Think - 生成思考
    const thought = await llm.think(`
      任务: ${task}
      上次观察: ${observation}
      思考你应该采取什么行动
    `);

    // 2. Act - 选择行动
    const action = await llm.selectAction(`
      思考: ${thought}
      可用工具: ${availableTools.map(t => t.name).join(', ')}
    `);

    if (action.type === 'finish') {
      return action.result;
    }

    // 3. 执行工具
    observation = await tools.execute(action.name, action.params);

    iteration++;
  }

  throw new Error('达到最大迭代次数');
}
```

### 6. Agent 配置

```markdown
## Agent 配置参数

| 参数 | 说明 | 推荐值 |
|-----|------|-------|
| model | 使用的模型 | gpt-4 / claude-3 |
| temperature | 创造性 | 0.0-0.3（Agent 通常较低） |
| max_tokens | 最大输出 | 2048-4096 |
| tools | 可用工具列表 | 按需配置 |
| verbose | 是否输出思考过程 | false（生产）/ true（调试） |
```

---

## 触发条件

当用户请求 AI Agent 设计、多智能体系统、工具调用实现、Agent 架构选型，或需要构建 AI 智能体时，自动应用此技能。
