# 公开迁移记录

两份原归档共 12,853 项。公开复核基于此前逐项审查过的本地候选，仅保留可确认来源并适合公开的配置与工程工具，源归档维持原状。

## 原归档处置汇总

| 原模块 | 原包项数 | 初始公开保留/提取 | 隔离待确认 | 排除已安装依赖及日志 |
| --- | ---: | ---: | ---: | ---: |
| Skills | 1,860 | 2 | 1,858 | 0 |
| Workspace | 10,993 | 4 | 13 | 10,976 |
| 合计 | 12,853 | 6 | 1,871 | 10,976 |

> 完整 12,853 项的逐区间原始审计表（原 `release-inventory.tsv`，含 312 条私有归档序号区间）已从公开主干移除，留存于私有迁移归档与初次导入提交记录中；下表保留所有实际公开条目的来源映射。

## 保留条目来源映射

| 原模块 | 来源序号 | 处置方式 | 目标路径 | 当前状态 |
| --- | --- | --- | --- | --- |
| Skills | `S001557` | 原依赖表逐字节保留 | `skills/http-validation/requirements.txt` | 保留 |
| Skills | `S001781` | 仅保留公共包依赖声明 | `skills/document-rendering/requirements.txt` | 保留 |
| Workspace | `W000001` | 通用工作约定 | `workspace/AGENTS.md` | 保留 |
| Workspace | `W000008` | 脱敏包锁定信息 | `workspace/package-lock.json` | 保留并裁剪无用浏览器依赖 `html2canvas`（327 → 322 项） |
| Workspace | `W000009` | 公共包配置 | `workspace/package.json` | 保留并裁剪 `html2canvas`（15 → 14 项直接依赖） |
| Workspace | `W010992` | 通用制作偏好 | `workspace/memory/MEMORY.md` | 已于后续精简移除（与当前公开模块无上下文关联） |

## 公开内容说明

- **技能依赖**：`skills/http-validation/requirements.txt` 与核对副本逐字节一致；`skills/document-rendering/requirements.txt` 仅保留原有 5 项必需依赖声明及次序。两份目录均采用通用命名，当前包含的原业务技能入口为 0。
- **Workspace**：保留通用工作约定 [AGENTS.md](../workspace/AGENTS.md) 以及 npm 依赖声明与锁文件。后续精简移除了 Node 环境中不适用的浏览器 DOM 库 `html2canvas` 及其 4 个独占传递依赖（剩余 322 个锁定项均保留原 SHA-512 完整性摘要）；第三方包代码由使用者按需从公共注册表安装。
- **项目工程文件**：静态检查器 [tools/check_repository.py](../tools/check_repository.py)、仓库检查入口 [skills/repository-check/SKILL.md](../skills/repository-check/SKILL.md) 与 [GitHub Actions](../.github/workflows/static.yml) 来自仓库整理，不计入原包 6 项。后续精简将静态检查改为纯 Python 标准库零依赖实现，并移除了冗余的 `.env.example` 与手工目录台账 `skill-modules.tsv`。

## 隔离依据

前次审查已隔离 1,583 项，涉及凭据或标识风险、地址和样例数据、不可核验文件名或二进制、历史材料及明确的复制限制。公开复核再隔离 288 项（其中 287 项来自技能，1 项为引用未公开本地模块的诊断脚本），两轮决定互不重复。

候选中仅标有许可证名称或无法确认实质代码与上游公开版本一致的模块、非公开操作说明、供应商接口、图片与模板均留待权利人复核。

## 验证与演进边界

- 静态检查覆盖已追踪文件路径与模式、UTF-8 编码、Python/JSON/TOML/INI 语法、`SKILL.md` 元数据、`skills/` 目录结构、`workspace` 依赖与锁文件一致性，以及基础凭据/本机路径护栏；全历史密钥扫描由 GitGuardian 等专用检查承担。
- 业务流程、外部服务、音视频处理与上游技能均未运行。原业务技能若要补充进仓库，应先定位对应来源序号，确认当前版本的公开授权与所需署名，并重新核查隐私与依赖。
