# 星穹智库（AstralArchives）

星穹铁道设定（角色、剧情、世界观）智能分析系统。

---

## 项目结构

```
AstralArchives/
├─ crawler/                # 爬虫相关（主流程、分类、页面、存储、日志）
│   ├─ __init__.py
│   ├─ crawl_main.py       # 主爬虫逻辑（原main.py迁移）
│   └─ run.py              # 预留爬虫入口
│   ...
├─ ui/                     # 命令行界面相关
│   ├─ __init__.py
│   ├─ main_menu.py        # 主菜单
│   ├─ readme_view.py      # rich展示README
│   ├─ crawl_view.py       # 爬虫启动界面
│   └─ config_view.py      # 分类管理界面（预留）
│   ...
├─ config/                 # 分类配置
│   └─ categories.json
├─ wiki/                   # 分类与页面源码存储（自动生成）
├─ log/                    # 运行日志（自动生成）
├─ main.py                 # 入口，只负责调度主菜单
├─ README.md               # 项目说明
├─ requirements.txt        # 依赖（可选）
├─ uv.toml                 # 依赖与虚拟环境配置（推荐uv）
```

---

## 使用说明

1. 安装依赖（推荐 [uv](https://github.com/astral-sh/uv)）：
   ```bash
   uv venv
   uv pip install -r uv.toml
   ```
2. 启动主菜单：
   ```bash
   python main.py
   ```
3. 按菜单提示操作。

## 主要功能

- rich 交互式命令行主菜单
- rich 渲染 README
- 爬虫高并发抓取 wiki 分类与页面
- 分类配置管理（预留）

## 目录说明

- `crawler/`    爬虫主流程与实现
- `ui/`         每个主菜单功能一个界面模块
- `config/categories.json` 分类配置
- `wiki/`       页面源码本地化存储
- `log/`        日志

---

> 本项目仅用于学习与交流，内容版权归米哈游及原作者所有。
