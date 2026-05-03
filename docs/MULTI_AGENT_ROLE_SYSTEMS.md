# Multi-Agent Role Systems Research - 2026-05-01

## 1. Role-Based Agent Framework

### Tianwen-AGI Roles

| Role | Description |
|------|-------------|
| COORDINATOR | Task assignment, coordination |
| PLANNER | Strategic planning, goal setting |
| EXECUTOR | Task execution |
| REVIEWER | Quality assurance, evaluation |
| RESEARCHER | Literature review, data analysis |
| HYPOTHESIS_GENERATOR | Scientific reasoning |
| OBSERVATION_SPECIALIST | Observation tasks |
| VLA_AGENT | Visual-language-action coordination |

## 2. GitHub Reference Projects

| Project | URL | Stars | Description |
|---------|-----|-------|-------------|
| AutoGPT | Significant-Gravitas/AutoGPT | 125k+ | Autonomous agent with self-reflection |
| HuggingGPT | microsoft/HuggingGPT | 25k+ | Multi-model collaboration |
| Voyager | MineDojo/Voyager | 15k+ | Skill library dynamic expansion |
| Generative Agents | bddppq/Generative-Agents | 15k+ | Interactive simulacra |

## 3. Dynamic Role Switching

Implemented in Tianwen-AGI via `CollaborationWorkflow`:
- Agents take different responsibilities based on task requirements
- Role assignment based on agent capabilities
- Context-aware role switching

## 4. Agent Skill Growth

From `Self-Evolution.md` and `skills/AI-Agent.md`:
- Three-layer learning: Instant, Periodic, Active
- Experience storage with success/failure patterns
- Skill self-creation from complex tasks
- Skill self-improvement based on feedback

## 5. Collaboration Patterns

| Pattern | Implementation |
|---------|----------------|
| Conflict Resolution | Priority裁决, consensus, expert裁决, compromise |
| VLA Integration | VLACoordinator for embodied AI |
| Safety | SafetyCoordinator for multi-agent safety |
| Research Loop | ResearchLoopAdapter for compatibility |

## 6. Key Observations

1. Role-based systems provide clarity and specialization
2. Dynamic role switching enables flexibility
3. Skill growth mechanisms are essential for long-term performance
4. Multi-agent coordination requires robust conflict resolution

## 7. References

- Tianwen-AGI: `runtime/multi_agent_coordinator.py`
- AutoGen: `microsoft/autogen`
- CAMEL: `camel-ai/camel`
- CrewAI: `crewAIInc/crewAI`
