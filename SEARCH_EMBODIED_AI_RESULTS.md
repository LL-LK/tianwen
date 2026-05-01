# Embodied AI Research - GitHub Search Results

**Date:** 2026-05-01

## Search Summary

Searched for open source projects related to Embodied AI in astronomical observatories, telescope control, and space robotics. The initial searches with specific astronomy terms yielded limited results, so broader searches were conducted.

---

## Relevant Projects Found

### 1. LLM-Robot-Control Projects (Most Relevant to Embodied AI)

| Project | URL | Stars | Description |
|---------|-----|-------|-------------|
| **llm-robot-control** | https://github.com/AlbertaBeef/llm-robot-control | 4 | LLM-based robot control experimentation |
| **voice-llm-robot-control** | https://github.com/PukyBots/voice-llm-robot-control | 0 | Voice-controlled robotic system powered by LLMs and ROS - natural language robot commanding |
| **multimodal-llm-robot-control** | https://github.com/MiloszAdamek/multimodal-llm-robot-control | 0 | LLM-based robot control integrating vision and natural language reasoning for real-time decision making |
| **morphology-generalizable-llm-robot-control** | https://github.com/ChaitanyaParate/morphology-generalizable-llm-robot-control | 0 | GNN-based RL with LLM planning, zero-shot transfer across robot structures in ROS2-Gazebo |
| **llm_robot_control** | https://github.com/YaoBeiji/llm_robot_control | 0 | VLA (Vision-Language-Action) multi-agent robot control |
| **lmt_ws** | https://github.com/St333fan/lmt_ws | 1 | Agentic compact-LLM Robot Control System |

**Key Features:**
- Natural language commanding of robots
- Vision-language integration
- ROS/ROS2/Gazebo simulation support
- Multi-agent architectures
- Zero-shot morphology transfer

### 2. Observatory Automation Projects

| Project | URL | Stars | Description |
|---------|-----|-------|-------------|
| **chimera** | https://github.com/astroufsc/chimera | 42 | Observatory Automation System (most stars) |
| observatory_automation | https://github.com/scubabri/observatory_automation | - | Scripts for mount, roof automation |
| labAutomation | https://github.com/mmastria/labAutomation | - | Astronomical Observatory Automation |
| observatory-automation | https://github.com/jd-stacey/observatory-automation | - | Recently updated (2026-04-30) |

**Key Features:**
- Telescope/mount control
- Roof automation
- Weather monitoring
- Safety controller integration

### 3. Physical Embodied Agent Robots

| Project | URL | Stars | Description |
|---------|-----|-------|-------------|
| **ESP32-Robot** | https://github.com/beixiangbei/ESP32-Robot | 0 | ESP32-S3 desktop embodied agent robot with camera, motors, OLED, I2S audio - HTTP REST API control |

---

## Observations

1. **Embodied AI + Astronomy Gap:** No directly relevant projects combining Embodied AI/LLM agents with astronomical telescopes/observatories were found. This represents an opportunity area.

2. **LLM Robot Control is Active:** Multiple projects explore LLM-based robot control with ROS, vision-language models, and natural language interfaces - these are directly applicable to telescope control.

3. **Observatory Automation is Mature but Separated:** Projects like Chimera (42 stars) show mature observatory automation, but none integrate modern Embodied AI/LLM capabilities.

4. **Key Technology Stack Observed:**
   - ROS/ROS2 for robot control
   - Gazebo for simulation
   - LLMs (via API or local) for reasoning
   - Vision-language models for perception
   - HTTP REST APIs for robot control (similar to telescope control)

---

## Recommendations for 天问-AGI

1. **借鉴 ESP32-Robot 架构:** Using HTTP REST API to control robots/telescopes is a proven pattern
2. **ROS2 集成:** Several projects use ROS2 - could integrate with existing telescope control systems
3. **Multi-agent架构:** YaoBeiji/llm_robot_control 的 VLA multi-agent 值得参考
4. **缺口:** 没有找到专门的"Embodied AI + 天文望远镜"项目，这是差异化机会