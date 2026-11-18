# 源码与开发

首次使用或由 Agent 协助，请先阅读 [中文指南](agent-guide.md) · [English guide](agent-guide.en.md)。

源码运行需要带 Tcl/Tk 的 Windows Python；本次开发环境为 Python 3.14.7、Tcl/Tk 9.0，打包使用 PyInstaller 6.22.3。

```powershell
python save_editor.py
python -B -m unittest discover
```

打包：

```powershell
python -m venv .build-env
.\.build-env\Scripts\python.exe -m pip install -r requirements-build.txt
.\build_exe.cmd
```

输出位置以 `build_exe.cmd` 为准。打包时需将 `editor_catalog.json` 嵌入单 EXE；编辑器运行、测试及普通打包无需原工程、游戏客户端或真实存档。重新生成目录需要自行构建并显式提供对应运行数据和原生库，见[目录来源](editor-catalog.md)。

- `save_editor.py`、`advanced_editor.py`：基础与深度界面、工作副本、预览、备份和保存。
- `editor_engine.py`、`editor_core/`：舰长、角色、装备、进度和舱室操作。
- `catalog_loader.py`、`editor_catalog.json`：V0.2.0 精简编辑目录与独立加载。
- `avatars.py`、`costumes.py`、`progression.py`：基础界面及兼容处理。
- `test_*.py`：目录、业务操作、保存和界面检查。

内置新号和体验号由 V0.2.0 目录生成，不复制真实账号，也不构造虚假的战斗结算；数据来源见 NOTICE。

Windows 发行物为单 EXE；Git 仓库不追踪构建产物。
