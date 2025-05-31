# 星穹智库（AstralArchives）

星穹铁道设定（角色、剧情、世界观）智能分析系统。

本项目通过高并发爬虫自动抓取 https://wiki.biligame.com/sr/ 的 MediaWiki 分类与页面内容，聚焦于角色、剧情、世界观等设定内容，不涉及战斗、数值、配队分析。

## 功能简介
- 支持 MediaWiki-API 高并发爬取
- rich 交互式命令行界面
- 分类可配置，按需抓取
- 分类与页面源码本地化存储

## 使用说明

### 环境准备
本项目推荐使用 [uv](https://github.com/astral-sh/uv) 进行依赖与虚拟环境管理。

- 初始化虚拟环境：`uv venv`
- 安装依赖：`uv pip install -r uv.toml`

### 启动方式
- 交互式（默认）：
  ```bash
  .venv/bin/python main.py
  ```
  自动按 config/categories.json 启用分类批量爬取。

- 指定分类（命令行参数）：
  ```bash
  .venv/bin/python main.py 分类1 分类2 ...
  ```
  只爬取指定分类（如：`NPC`）。

### 目录结构
- `./config/` 分类配置文件（首次运行自动生成）
- `./wiki/` 分类与页面源码存储

如需添加依赖，请编辑 `uv.toml` 并用 `uv pip install`。

---

> 本项目仅用于学习与交流，内容版权归米哈游及原作者所有。
