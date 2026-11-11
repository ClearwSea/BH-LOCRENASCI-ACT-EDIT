# 来源与许可

## 本项目代码

GUI、白名单编辑、备份、模板及进度处理来自现有 BH3 V1.9 存档修改器 v0.7。此目录是独立发布候选稿，不含游戏客户端、服务端、连接配置或真实用户存档。

项目原创代码采用 MIT License，Copyright (c) 2026 ClearwSea，完整条款见 LICENSE。模板中的“禁止倒卖”是历史提示文字，不构成对 MIT 授权的附加限制；MIT 许可允许商业使用与再分发。

## 数据来源

关卡标识和开放约束整理自 nx-compat.1 / server19 common.2 兼容表，记录在 `catalog_provenance.json`。两个账号模板由已知初始配置及演示档的角色配装规则整理生成；体验号使用已验证装备目录，不携带旧账号抽卡、充值、聊天历史。游戏相关名称、标识及数据的权利属于相应权利人，不能由本项目许可证重新授权。

## 运行与打包组件

- Python：PSF 许可及随附声明，见 `licenses/Python-LICENSE.txt`。
- Tcl/Tk：Tk 许可文本见 `licenses/Tk-license.terms`；Python 随附声明亦须保留。
- PyInstaller：GPL 及其分发例外，见 `licenses/PyInstaller-COPYING.txt`。构建钩子版本固定于 requirements-build.txt。

这些组件的条款与本项目的 MIT 许可证分别适用。

服装目录仅含46套服装标识与适用角色映射，来自V0.1.5 ARM32兼容表；来源指纹见 `costume_catalog.json`，不含图片或真实账号数据。
The costume catalog contains identifiers and avatar mappings only, derived from the compatible V0.1.5 ARM32 table; provenance is recorded in costume_catalog.json.
