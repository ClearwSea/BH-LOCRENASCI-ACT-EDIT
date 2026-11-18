# 来源与许可

## 本项目代码

GUI、白名单编辑和备份基于既有 BH3 V1.9 存档编辑器；深度编辑中的纯数据操作改编自 BH2017-LOCRENASCI V0.2.0 对应源码。项目不包含游戏客户端、完整运行服务端、连接配置或真实用户存档。

项目原创代码采用 MIT License，Copyright (c) 2026 ClearwSea，完整条款见 LICENSE。模板中的“禁止倒卖”是历史提示文字，不构成对 MIT 授权的附加限制；MIT 许可允许商业使用与再分发。

## 数据来源

旧版关卡标识和开放约束整理自 nx-compat.1 / server19 common.2 兼容表，记录在 `catalog_provenance.json`。新增 `editor_catalog.json` 从用户自备的 BH2017-LOCRENASCI V0.2.0 完整构建运行数据中提取，仅保留编辑字段、约束和引用的名称；来源指纹与生成方法见 `docs/editor-catalog.md`。新号和体验号由精简目录生成，不包含真实账号的抽卡、充值或聊天历史。游戏相关名称、标识及数据的权利属于相应权利人，不能由本项目许可证重新授权。

## 运行与打包组件

- Python：PSF 许可及随附声明，见 `licenses/Python-LICENSE.txt`。
- Tcl/Tk：Tk 许可文本见 `licenses/Tk-license.terms`；Python 随附声明亦须保留。
- PyInstaller：GPL 及其分发例外，见 `licenses/PyInstaller-COPYING.txt`。构建钩子版本固定于 requirements-build.txt。

这些组件的条款与本项目的 MIT 许可证分别适用。

服装目录仅含46套服装标识与适用角色映射，来自V0.1.5 ARM32兼容表；来源指纹见 `costume_catalog.json`，不含图片或真实账号数据。
The costume catalog contains identifiers and avatar mappings only, derived from the compatible V0.1.5 ARM32 table; provenance is recorded in costume_catalog.json.
