# Kangge Agent Platform

一个分为 Skills 与 Workspace 的单仓库。审阅分支提供仓库静态检查工具、可复用的依赖配置，以及经过脱敏的工作约定。

| 路径 | 内容 |
| --- | --- |
| [skills/](skills/README.md) | 仓库检查技能和两份模块依赖清单 |
| [workspace/](workspace/) | npm 依赖与锁文件、AGENTS.md 和通用制作偏好 |
| [tools/check_repository.py](tools/check_repository.py) | 检查技能入口、Python 语法、配置格式和 Git 对象 |
| [docs/](docs/public-release.md) | 公开版与原归档的对应关系、隔离数量和核验边界 |

## 运行静态检查

在仓库根目录使用 Python 3.11 或更高版本。

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --no-deps --only-binary=:all: PyYAML==6.0.3
python -I tools/check_repository.py
```

命令只读取文件和 Git 对象。PR 上的 GitHub Actions 使用同一入口。检查器还会识别历史中的常见凭据格式、私钥、签名参数、个人联系方式以及禁止纳入的文件类型。新增业务资产仍需单独核实公开权限与隐私。

## 安装模块依赖

在 `workspace/` 中运行以下命令。锁文件记录第三方包的版本与 SHA-512 摘要，npm 从公共注册表获取依赖，安装过程中禁用生命周期脚本。

```sh
npm ci --registry=https://registry.npmjs.org --ignore-scripts --no-audit --no-fund
```

在两个 Python 依赖目录中，分别启用自己的虚拟环境，再运行 `python -m pip install --only-binary=:all: -r requirements.txt`。原 ZIP 提供了范围约束；安装时选用范围内支持当前平台的版本。这两份清单不含业务脚本。检查器和公开配置均无需业务凭据。可选的 npm 本地缓存目录见 [.env.example](.env.example)。

## 版本与审阅

`main` 的引导提交仅含 README。此次整理在 `migration/initial-import` 分支提交，通过 PR 审阅。Workspace 的依赖更新同时维护 package.json 和 package-lock.json。修改技能入口时同步维护 [模块清单](docs/skill-modules.tsv)。本次未为原业务技能或仓库整体指定新许可证。
