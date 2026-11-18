# 存档编辑目录来源

`editor_catalog.json` 是为 PC 存档编辑器准备的只读索引，供编辑器离线加载。它从 BH2017-LOCRENASCI V0.2.0 完整构建的运行数据提取；对应运行包清单 SHA-256 为 `b47ea2d597015d09ada37453a2258e7fa0e1c4d5dd64fed2dcdf15c12a749b56`。它不包含存档、图片、音视频或本机路径。

目录仅保留编辑器必需的角色、共享技能、服装、装备、材料、等级约束、3–5 号舱室、剧情/外传前置与星级、轮回和深渊字段。关卡挑战项只保留数量，不包含奖励数据；名称仅保留被引用的文本。源数据本身缺少部分名称时，编辑器以 ID 或文本键显示，不推测名称。

目录是从用户提供的游戏数据派生的兼容索引；游戏名称和相关内容的权利属于其权利人。原始游戏客户端和完整表单不随本项目提供。既有模板及目录的来源还见 `NOTICE.md` 和 `catalog_provenance.json`。

运行编辑器不需要游戏构建产物。开发者如需重新生成，先自行按 BH2017-LOCRENASCI 构建得到已验证的 V0.2.0 运行目录及其对应原生库，再显式指定两者：

```powershell
python -B tools/build_editor_catalog.py --runtime <运行目录> --native <对应原生库> --output editor_catalog.json
python -B -m unittest test_catalog_loader
```

生成器通过原运行包的校验流程核对清单与原生库，使用独立临时目录初始化，不读取用户存档，并只输出上述字段。打包时应将 `editor_catalog.json` 放到应用资源根目录；`catalog_loader.py` 支持源码运行和 PyInstaller 临时资源目录。
