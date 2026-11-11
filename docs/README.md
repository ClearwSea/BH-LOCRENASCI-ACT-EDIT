# 源码与开发

首次使用或由 Agent 协助，请先阅读 [中文指南](agent-guide.md) · [English guide](agent-guide.en.md)。

建议使用带 Tcl/Tk 的 Windows Python 3.13。验证环境：Python 3.13.15、PyInstaller 6.22.3。

```powershell
python save_editor.py
python -B -m unittest test_save_editor
```

打包：

```powershell
python -m venv .build-env
.\.build-env\Scripts\python.exe -m pip install -r requirements-build.txt
.\build_exe.cmd
```

输出为 `dist/BH3-V1.9-Save-Editor.exe`。运行、测试及打包均使用仓库附带的关卡目录和模板，无需原工程或游戏客户端。

- `save_editor.py`：界面、输入校验、模板只读字段、文件备份和保存。
- `progression.py`：剧情、外传、轮回与深渊逻辑。
- `stage_catalog.json`：最小关卡目录。
- `costumes.py` / `costume_catalog.json`：服装持有编辑与46套服装的角色适配标识。
- `templates/`：预生成的新号和体验号。
- `test_save_editor.py`：保存安全、字段边界、模板及进度测试。

原工程的模板生成脚本依赖私有工程布局和原始表，此候选仓库不包含该脚本或输入。开发时直接维护预生成模板并运行测试；数据来源见 NOTICE。

Windows ZIP 作为 GitHub Release 附件提供，Git 仓库保留版本说明和校验值，不追踪二进制包。
