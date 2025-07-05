# 星穹智库（AstralArchives）

> 崩坏：星穹铁道设定（角色、剧情、世界观）智能分析与上下文感知检索系统

---

## 项目简介

星穹智库是面向《崩坏：星穹铁道》Wiki数据的智能分析与检索平台，支持多轮对话、上下文感知检索、RAG问答、分片嵌入、配置驱动提示词等全流程，适合知识库、AI问答、内容分析等场景。

---

## 主要特性

- **多轮对话与上下文感知**：支持连续多轮对话，自动处理指代、省略、上下文承接，检索关键词提取模型可结合历史对话理解用户真实意图。
- **RAG智能问答**：每轮自动检索设定资料，结合历史对话与资料片段生成结构化Markdown答案。
- **配置驱动提示词**：所有提示词均集中于 `config/prompts.json`，无需修改代码即可灵活调整对话、检索、分析等行为。
- **Token消耗统计**：每轮自动显示Prompt和LLM输出的Token数，便于控制上下文长度和成本。
- **Rich命令行交互**：主界面支持多轮输入、资料检索开关、元数据表格展示、Markdown渲染等。
- **高并发异步爬虫**：支持多分类并发抓取，自动本地化存储页面源码。
- **结构化数据清洗**：支持多分类，统一输出结构化JSON。
- **向量化嵌入与检索**：分片嵌入，全部内容、元数据、索引自包含于单一zip文件，检索无需外部元数据。
- **依赖管理现代化**：推荐 `venv` + `uv`，安装快、兼容性好。
- **OpenAI API兼容RAG服务端**：支持标准OpenAI /v1/chat/completions接口，流式/非流式全兼容，支持chatbox、openai官方库、curl等多种客户端。

---

## 目录结构

```
AstralArchives/
├─ crawler/                # 爬虫主流程与实现
├─ datacleaner/            # 数据清洗主流程与各分类模型
├─ ui/                     # rich命令行界面与各功能入口
├─ config/                 # 分类配置、API密钥、prompts.json
├─ wiki/                   # 页面源码本地化存储（自动生成）
├─ wiki_cleaned/           # 清洗后结构化json（自动生成）
├─ db/                     # 向量数据库（如wiki_allinone.zip）
├─ log/                    # 运行日志（自动生成）
├─ main.py                 # 菜单入口
├─ RAGCUI.py               # rich多轮智能问答主界面
├─ devCUI.py               # 其它功能入口
├─ llm_api.py              # OpenAI兼容API服务端
├─ README.md               # 项目说明
├─ pyproject.toml          # 依赖与元数据配置
```

---

## 快速开始

1. **环境准备**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install uv
   uv sync
   ```
2. **配置API密钥**
   - 复制 `config/api_keys.template.json` 为 `config/api_keys.json`，填写你的嵌入API密钥。
3. **启动主菜单**
   ```bash
   python main.py
   ```
4. **进入RAG多轮问答界面**
   ```bash
   python RAGCUI.py
   ```
5. **启动OpenAI兼容API服务端**
   ```bash
   uvicorn llm_api:app --host 0.0.0.0 --port 8080
   ```
6. **用chatbox、openai库、curl等客户端对接API**
   - API地址：`http://<服务器IP>:8080/v1`
   - API Key：`test`
   - 完全兼容OpenAI官方API格式，支持流式/非流式、历史对话、token统计、Markdown结构化输出。

---

## OpenAI兼容API说明

- **接口路径**：`/v1/chat/completions`
- **请求参数**：
  - `model`：必须为`AstralArchives`
  - `messages`：历史对话，格式同OpenAI
  - `stream`：是否流式输出
  - 其他参数会被忽略
- **响应内容**：
  - `choices[0].message.content`（非流式）或`choices[0].delta.content`（流式）为完整结构化答案，分为检索关键词、元数据表（Markdown，单元格超长自动...截断）、分析结果三部分
  - `usage`字段返回token消耗统计
  - 完全兼容openai官方库、chatbox、curl等
- **流式输出**：
  - 每个chunk以`data: `开头，`\n\n`结尾，最后`data: [DONE]\n\n`，Content-Type为`text/event-stream`
- **跨域支持**：已内置CORS中间件，前端/移动端可直接跨域访问

---

## 主要命令与功能

- `python RAGCUI.py`：进入 rich 智能多轮问答界面（支持上下文感知检索、Token统计、配置驱动提示词）
- `python RAGCUI.py --test`：自动批量测试典型问题，输出至 output/A1.md、B1.md、C1.md
- `python devCUI.py`：
  - 查看README
  - 启动爬虫（自动抓取已启用分类）
  - 管理分类（批量启用/禁用）
  - 清洗数据（结构化输出json，带进度条）
  - 数据嵌入（分片、进度条、全自包含zip向量库）
  - 检索数据（输入关键词，返回前十条分片元数据）
- `uvicorn llm_api:app --host 0.0.0.0 --port 8080`：启动OpenAI兼容API服务端

---

## Chatbox/第三方客户端对接

- 推荐使用 [chatbox](https://github.com/Bin-Huang/chatbox) 或任何支持OpenAI API的客户端
- API地址填写 `http://<服务器IP>:8080/v1`
- API Key填写 `test`
- 支持流式/非流式、历史对话、Markdown渲染、token统计等

---

## 常见问题排查

- **端口无法访问/超时**：
  - 确认服务端用`--host 0.0.0.0`启动，端口未被占用
  - 检查防火墙/路由器端口隔离/端口过滤/无线隔离等
  - 建议优先用8080等常用端口
- **chatbox/网页无响应**：
  - 确认API服务端已加CORS中间件
  - 确认API Key为`test`，API地址为`http://<服务器IP>:8080/v1`
  - 检查局域网互通性
- **API格式不兼容**：
  - 已严格对齐OpenAI官方API格式，流式/非流式均兼容
  - 如遇特殊客户端兼容性问题请反馈
- **表格内容过长**：
  - 单元格超30字符自动截断并加`...`标志

---

## 配置与自定义

- **所有提示词均在 `config/prompts.json` 配置**，包括system_prompt、多轮对话格式、检索关键词提取、RAG主流程等。
- 支持灵活调整对话风格、检索策略、输出格式，无需修改代码。

---

## 依赖与适配

- Python 3.11+
- 依赖见 `pyproject.toml`，推荐用 `uv` 安装
- 需联网访问嵌入API（如 BAAI/bge-m3、OpenAI等）

---

## 免责声明

- 本项目仅用于学习与交流，内容版权归米哈游及原作者所有。
- 向量化API需自备密钥，使用第三方API请遵守相关服务条款。
