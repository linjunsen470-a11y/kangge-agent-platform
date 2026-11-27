# Kangge Agent Platform

这个仓库包含 Skills 与 Workspace 两个模块，保留了可复用的依赖配置、脱敏工作约定和通用制作偏好。

| 路径 | 内容 |
| --- | --- |
| [skills/](skills/README.md) | 仓库检查技能入口和两份模块 Python 依赖清单 |
| [workspace/](workspace/) | npm 依赖与锁文件、[工作约定](workspace/AGENTS.md) 和[通用制作偏好](workspace/memory/MEMORY.md) |
| [tools/check_repository.py](tools/check_repository.py) | 检查当前文件、技能入口、配置语法、锁文件和 Git 历史 |
| [docs/public-release.md](docs/public-release.md) | 公开迁移记录、保留来源映射、隔离统计与核验边界 |

## 运行静态检查

在完整克隆的仓库根目录，使用 Python 3.11 或更高版本创建环境并安装锁定版本的 YAML 解析器。浅克隆请先运行 `git fetch --unshallow`。

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --no-deps --only-binary=:all: -r tools/requirements.txt
.venv/bin/python -I tools/check_repository.py
.venv/bin/python -I -m unittest discover -s tests
```

检查器验证当前已追踪文件的目录结构、Python 语法、JSON/YAML/TOML/INI 配置、技能入口和 Workspace 根依赖。它还扫描当前提交及本地各引用可达的历史文件、路径、提交和标签，检查常见凭据及个人标识。Git 身份字段中的邮箱仅豁免联系地址规则，提交说明、标签说明和文件内容中的邮箱仍受检查。

PR 的 CI 在 GitHub 生成的预合并版本上运行同一组命令。GitGuardian 提供独立的补充检查。新增业务资产仍需人工核实公开授权与隐私。[GitHub Actions 配置](.github/workflows/static.yml)

## 安装模块依赖

在 `workspace/` 中运行以下命令（锁文件记录第三方包版本与 SHA-512 摘要，安装时禁用生命周期脚本）：

```sh
npm ci --registry=https://registry.npmjs.org --ignore-scripts --no-audit --no-fund
```

如需指定本地 npm 缓存目录，可在调用命令时通过环境变量 `NPM_CONFIG_CACHE` 传入。若后续实际运行依赖浏览器的脚本，需另行安装 Playwright 浏览器二进制。

在两个 Python 依赖目录中，分别启用独立虚拟环境后执行：

```sh
python -m pip install --only-binary=:all: -r requirements.txt
```

两份清单仅含公共包范围约束，不含业务脚本；检查器和公开配置均无需任何业务凭据。

## 维护与审阅

- 更新 `workspace/package.json` 时需同步维护 `workspace/package-lock.json`（若使用公共源重生成标准锁文件，可运行 `npm install --package-lock-only --registry=https://registry.npmjs.org`）。
- `skills/` 下的目录结构由 [tools/check_repository.py](tools/check_repository.py) 自动校验（完整技能需含 `SKILL.md`，仅依赖目录需含 `requirements.txt`），无需额外维护手工清单表。
- 当前仓库尚未为整体或原业务技能指定统一开源许可证，公开复用前请先确认许可证归属。
