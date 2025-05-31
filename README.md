# 星穹智库（AstralArchives）

星穹铁道设定（角色、剧情、世界观）智能分析系统。

---

## 新版本亮点

- **全新 rich 交互式命令行主菜单**，支持一键查看 README、启动爬虫、管理分类。
- **分类管理界面**：支持多选、批量启用/禁用、分页浏览，操作直观。
- **高并发异步爬虫**：支持多分类并发抓取，自动本地化存储页面源码。
- **配置与日志分离**：所有配置、日志、wiki源码均有独立目录，结构清晰。
- **依赖管理升级**：推荐使用 `venv` + `pip install uv` + `uv sync`，更快更稳定。

---

## 项目结构

```
AstralArchives/
├─ crawler/                # 爬虫相关（主流程、分类、页面、存储、日志）
│   ├─ __init__.py
│   ├─ crawl_main.py       # 主爬虫逻辑
│   └─ run.py              # 预留爬虫入口
├─ ui/                     # 命令行界面相关
│   ├─ __init__.py
│   ├─ main_menu.py        # 主菜单
│   ├─ readme_view.py      # rich展示README
│   ├─ crawl_view.py       # 爬虫启动界面
│   └─ category_manage_view.py # 分类管理界面
├─ config/                 # 分类配置
│   └─ categories.json
├─ wiki/                   # 分类与页面源码存储（自动生成）
├─ log/                    # 运行日志（自动生成）
├─ main.py                 # 入口，只负责调度主菜单
├─ README.md               # 项目说明
├─ pyproject.toml          # 依赖与元数据配置
```

---

## 环境配置与安装

1. **创建虚拟环境**（推荐 Python 3.8+）：
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. **安装 uv（推荐使用 uv 代替 pip，速度更快）：**
   ```bash
   pip install uv
   ```
3. **同步依赖**（自动读取 pyproject.toml）：
   ```bash
   uv sync
   ```

---

## 使用说明

1. 启动主菜单：
   ```bash
   python main.py
   ```
2. 按菜单提示操作：
   - 查看 README
   - 启动爬虫（自动抓取已启用分类）
   - 管理分类（批量启用/禁用）

---

## 主要功能

- rich 交互式命令行主菜单
- rich 渲染 README
- 高并发异步爬虫，自动本地化存储 wiki 页面源码
- 分类配置管理（批量、分页、直观）
- 日志自动记录

---

## 目录说明

- `crawler/`    爬虫主流程与实现
- `ui/`         每个主菜单功能一个界面模块
- `config/categories.json` 分类配置
- `wiki/`       页面源码本地化存储
- `log/`        日志

---

> 本项目仅用于学习与交流，内容版权归米哈游及原作者所有。
