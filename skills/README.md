# Skills

| 目录 | 状态 | 内容 | 使用方式 |
| --- | --- | --- | --- |
| [repository-check](repository-check/SKILL.md) | 完整入口 | 本项目的静态检查与 Git 历史扫描 | 按[仓库说明](../README.md#运行静态检查)准备环境后，运行 `.venv/bin/python -I tools/check_repository.py` |
| [http-validation](http-validation/requirements.txt) | 仅依赖 | 原包的 2 项 Python 包名与版本约束 | 使用独立虚拟环境安装该目录的 `requirements.txt` |
| [document-rendering](document-rendering/requirements.txt) | 仅依赖 | 原依赖清单保留的 5 项必需包与版本约束 | 使用独立虚拟环境安装该目录的 `requirements.txt` |

两个仅依赖目录供重新准备模块环境使用，原业务实现和模板仍待发布权确认。原渲染依赖表另列有可选的 OpenCV，仅在需要图像处理时单独评估；若实际使用 Playwright，需另行安装浏览器内核。来源序号及迁移记录见 [公开迁移记录](../docs/public-release.md)。
