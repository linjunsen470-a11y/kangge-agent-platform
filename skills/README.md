# Skills

| 目录 | 内容 | 使用方式 |
| --- | --- | --- |
| repository-check | 本项目编写的静态检查入口 | 在仓库根目录运行入口中列出的命令 |
| http-validation | 原包的两项 Python 包名与版本约束，内容逐字节保留 | 使用独立虚拟环境安装该目录的 requirements.txt |
| document-rendering | 从原依赖清单保留的五项必需包与版本约束 | 使用独立虚拟环境安装该目录的 requirements.txt |

两个依赖目录供重新准备模块环境使用。原业务实现和模板仍待发布权确认。原渲染依赖表另列有可选的 OpenCV，只有需要图像处理时才需单独评估。来源序号及决定见 [公开迁移记录](../docs/public-release.md)。
