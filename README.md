# Kangge Agent Platform

这个仓库提供一个可运行的仓库检查技能，以及开发房产业务工具所需的 Node.js 和 Python 依赖清单。业务脚本和模板需自行编写或经授权接入。

- 楼盘报告、成交图表和图片处理的用途见[房产业务应用场景](docs/real-estate-scenarios.md)。
- 安装依赖、更新锁文件或新增技能，请查阅[使用指南](docs/usage-guide.md)和[技能目录](skills/README.md)。
- 工作区约定包括[文件与交付](workspace/AGENTS.md)和[视频制作偏好](workspace/memory/MEMORY.md)。
- 公开范围、来源及隔离原因见[迁移记录](docs/public-release.md)。

## 运行静态检查

在完整克隆的仓库根目录使用 Python 3.11+。浅克隆请先执行 `git fetch --unshallow`。首次运行时准备检查环境。

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --no-deps --only-binary=:all: -r tools/requirements.txt
```

提交前先暂存新增文件，用 `git diff --cached` 核对即将提交的内容，再手动运行检查器和回归测试。

```sh
.venv/bin/python -I tools/check_repository.py
.venv/bin/python -I -m unittest discover -s tests
```

检查器读取已跟踪文件的工作副本，校验路径、语法、配置和技能结构，并扫描这些文件及可达 Git 历史中的常见凭据和个人标识。Git 身份字段和标准 `Co-authored-by:` 尾注中的邮箱仅豁免联系地址规则。

创建或更新 PR 后，GitHub Actions 会检查预合并版本，GitGuardian 会单独报告扫描结果。推送到 `main` 也会触发静态检查。公开新资产前仍需人工核实隐私和再发布授权。[CI 配置](.github/workflows/static.yml)
