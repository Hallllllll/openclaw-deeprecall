# 🧠 DeepRecall for OpenClaw

> **首个为 AI Agent 设计的全生命周期记忆管理系统。本地运行、SQLite 驱动、完美集成 LLM 总结能力。**

[English](README.md) | [简体中文](README_zh-CN.md)

[![OpenClaw Compatible](https://img.shields.io/badge/OpenClaw-Skill-blue.svg)](#)
[![Local First](https://img.shields.io/badge/Privacy-100%25_Local-success.svg)](#)
[![LLM Summarizer](https://img.shields.io/badge/LLM-Summarizer_Integrated-blueviolet.svg)](#)

DeepRecall 是 OpenClaw 的一套完整记忆操作系统，涵盖了**数据摄取 (L1/L2)、精准检索、以及上下文优化 (阅后即焚)**。

## 🔄 全生命周期工作流

DeepRecall 通过三个集成阶段管理 Agent 的记忆：

1.  **记忆摄取 (Summarizer):** - 自动扫描 `memory/*.md` 会话文件。
    - 自动从 `openclaw.json` 读取配置，调用 LLM (DeepSeek, Qwen 等) 将原始日志提炼为结构化 L1 事实。
    - 同步原始内容至本地 L2 SQLite 归档。
2.  **记忆检索 (Engine):**
    - Agent 通过 `search_memory_db` 快速锁定 L1 指针。
    - 如需细节，通过 `read_archive_db` 对 L2 归档进行精准提取。
3.  **上下文优化 (阅后即焚):**
    - 提取完成后，物理删除临时 `.md` 文件，确保 Agent 的上下文窗口始终保持极轻量状态。

## 📸 执行日志 (两级精准寻址)

> Agent 任务: "提取上周复盘中的 Vue 沙箱报错代码。"

[0.01s] 🧠 逻辑: 正在 L1 事实库中搜索 "Vue 沙箱"...
[0.02s] ⚡️ L1 命中: [2026-03-06-dead-code.md] 包含具体沙箱报错。
[0.08s] 🔍 L2 深挖: 正在从归档中提取精确代码段...
[0.09s] 🔥 阅后即焚: 已从活跃上下文中释放 "2026-03-06-dead-code.md"。
[0.10s] ✅ 成功: 本轮节省约 15,420 Tokens。

🚀 核心特性

多模型总结: 原生支持 DeepSeek、通义千问等主流模型做自动化索引。

数据主权: 所有的总结事实和原始归档 100% 存储在本地 SQLite 中。

零配置自举: 动态检测 OPENCLAW_WORKSPACE 环境，自动读取 API 配置。

拒绝幻觉: 通过精准指针而非海量文本块，使 Agent 的检索准确率逼近 100%。

📦 安装指南

```bash
clawhub install deeprecall
```

🛠️ 集成工具

summarize_memory_files: 触发 LLM 将原始日志加工入库。

search_memory_db: 搜索 L1 结构化事实。

read_archive_db: 精准提取 L2 原始内容。

🛡️ 安全与隐私说明

权限: 为了实现“阅后即焚”特性，本技能需要本地文件读写与删除权限。

存储: L1 事实在 SQLite 中永久保存。所有数据绝对保留在你的本地设备上。

环境变量: 代码读取 OPENCLAW_WORKSPACE 环境变量以实现自动寻址。
