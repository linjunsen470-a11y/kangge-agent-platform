# Kangge Agent Platform

一个分为 Skills 与 Workspace 的单仓库，提供零外部依赖的仓库静态检查工具、可复用的模块依赖配置，以及脱敏后的通用工作约定。

| 路径 | 内容 |
| --- | --- |
| [skills/](skills/README.md) | 仓库检查技能入口和两份模块 Python 依赖清单 |
| [workspace/](workspace/) | npm 依赖与锁文件，以及 [AGENTS.md](workspace/AGENTS.md) 通用工作约定 |
| [tools/check_repository.py](tools/check_repository.py) | 基于 Python 标准库的静态检查脚本（路径规范、语法配置、技能入口、基础凭据护栏与锁文件一致性） |
| [docs/public-release.md](docs/public-release.md) | 公开迁移记录、保留来源映射、隔离统计与核验边界 |

## 运行静态检查

在仓库根目录使用 Python 3.11 或更高版本，无需创建虚拟环境或安装第三方依赖：

```sh
python3 -I tools/check_repository.py
```

命令仅读取本地已追踪文件，PR 与 `main` 上的 [GitHub Actions](.github/workflows/static.yml) 使用同一入口。该脚本负责仓库结构、Python/JSON/TOML/INI 语法、`SKILL.md` 元数据、`workspace` 依赖与锁文件一致性以及常见私钥/凭据/本机路径护栏检查；全历史深度密钥扫描由 GitHub 上的 GitGuardian 等专用工具承担。新增业务资产前仍需单独核实公开授权与隐私。

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
