# 🧠 DeepRecall for OpenClaw

> **100% 本地化、SQLite 驱动的 L1/L2 双层记忆引擎。彻底告别无脑向量检索导致的 Token 膨胀，采用“索引寻址 + 按需深挖”的硬核架构。**

[English](README.md) | [简体中文](README_zh-CN.md)

[![OpenClaw Compatible](https://img.shields.io/badge/OpenClaw-Skill-blue.svg)](#)
[![Local First](https://img.shields.io/badge/Privacy-100%25_Local-success.svg)](#)
[![Zero Config](https://img.shields.io/badge/Setup-Zero_Config-orange.svg)](#)

## 🛑 核心痛点

市面上大多数 AI Agent 记忆插件要么依赖云端 SaaS（存在隐私泄露风险），要么使用简单的向量检索（Vector Search），把大段原始 Markdown 直接塞进上下文。这会导致严重的**上下文污染、极高的 Token 开销以及大模型幻觉**。

## ⚡️ 解决方案：L1/L2 双层架构

DeepRecall 为大语言模型 Agent 引入了类似 CPU 多级缓存的记忆机制：

* **L1 缓存 (结构化事实):** 高度压缩的 SQLite 数据表，仅存储提炼后的核心事实与文件指针。作为 Agent 的“日常上下文”，Token 成本极低。
* **L2 归档 (原始文件):** 完整的历史对话或代码文件。Agent 被严格限制**禁止**直接扫描 L2。只有当它在 L1 中找到明确的 `source_file` 指针时，才会精准下潜读取 L2。
* 🔥 **阅后即焚机制 (Read-and-Burn):** 一旦 Agent 从 L2 归档中提取到所需的确切片段（例如一段具体的报错代码），它会立即将这个巨大的源文件从活跃的上下文窗口中释放掉，绝不浪费一个 Token。

## 📸 实战演示 (内部执行日志)

以下是 Agent 使用 DeepRecall 跨越时间周期，精准检索上周复杂 Bug 报错信息的真实内部执行追踪：


> Agent 任务: "查一下上周复盘的 Vue 静默失效的三个原因，并提取包含变量插值的沙箱报错代码。"

[System] 启动 DeepRecall L1/L2 检索引擎...

[0.02s] ⚡️ L1 缓存命中 (结构化事实)
> Tool: search_memory_db(query="Vue 静默失效 OR 沙箱报错", limit=5)
  ├─ 事实 1: [2026-03-05 | learnings | pointer: 2026-03-05-vue-render.md] 
  │  原因: setup() 返回缺失、HTML标签未闭合、v-if 逻辑错误。
  └─ 事实 2: [2026-03-06 | learnings | pointer: 2026-03-06-dead-code.md] 
     沙箱验证失败（经过3次尝试）。(需要深入 L2 获取精确代码)

[0.08s] 🔍 L2 归档深挖 (原始内容)
> Tool: read_archive_db(source_file="2026-03-06-dead-code.md")
  └─ 精准提取 215-220 行...
     找到代码: `await self.fail_task(task['id'], f"沙箱验证失败：经过3次尝试仍无法通过。最后错误：{stderr[:500]}")`

[0.09s] 🔥 上下文管理
> Action: Read-and-Burn (阅后即焚)
> Status: 正从活跃上下文窗口中物理释放 "2026-03-06-dead-code.md"。
  └─ Token 收益: 成功回收约 15,420 Tokens。

[0.10s] ✅ DeepRecall 检索流程完毕。开始向用户生成回复...

🚀 核心特性
100% 本地隐私: 无需 API Key，不上传云端。所有数据绝对保留在你的本地机器上。

零配置自举 (Self-Bootstrapping): 安装即用。自动创建 SQLite 数据库，自动构建表结构并维护自身状态。

极致 Token 优化: 过滤所有冗余元数据，只把最纯粹的干货喂给 LLM。

📦 安装指南
在你的 OpenClaw 环境中全局安装 DeepRecall，只需执行：

Bash
clawhub install deeprecall

🛠️ 注册工具
安装完成后，你的 Agent 会自动获得以下两个工具的访问权限：

search_memory_db(query: str, limit: int) - 用于 L1 语义与关键词检索。

read_archive_db(source_file: str) - 在 L1 指针引导下，用于 L2 原始数据的精准提取。

Built with ❤️ for the OpenClaw Community.
