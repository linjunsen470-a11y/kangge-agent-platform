# 项目使用指南（快速看懂这个仓库能干什么、怎么用）

这份文档面向人类读者与日常协作者，用最直观的方式说明本仓库的定位、能力边界以及常见用法。

---

## 一、这个项目能干什么？

**Kangge Agent Platform** 是一个面向 AI Agent（智能体）的 **技能（Skills）与工作区（Workspace）公开底座仓库**。它的目标是把原本分散在本地归档中的可复用工具环境、协作约定和合规检查沉淀成一个干净、可审计、可持续扩展的公开工程骨架。

目前仓库已经开箱可用的 4 项核心能力：

1. **仓库安全与规范体检（立即可用）**
   - 内置 [tools/check_repository.py](../tools/check_repository.py) 和对应的 Agent 技能入口 [skills/repository-check/SKILL.md](../skills/repository-check/SKILL.md)。
   - 可以在本地或 GitHub Actions 中自动检查：Python/JSON/YAML/TOML/INI 语法、`SKILL.md` 格式、`workspace` 依赖与锁文件一致性、跨平台大小写/Unicode 文件名冲突，以及代码和 Git 历史中是否误提交了私钥、凭据、压缩包、敏感路径或个人联系方式。
2. **Workspace Node.js 工具包底座（可直接安装复用）**
   - [workspace/package.json](../workspace/package.json) 和 [workspace/package-lock.json](../workspace/package-lock.json) 预置了 14 个常用工具包（共 322 项锁定依赖），方便后续脚本或 Agent 直接调用：
     - **办公文档生成与解析**：Word（`docx`）、PPT（`pptxgenjs`、`@aiden0z/pptx-renderer`）、Excel（`exceljs`）、CSV（`csv-parse`、`@json2csv/plainjs`）、Markdown（`marked`）。
     - **数据可视化与图像处理**：图表渲染（`echarts`、`d3`）、图片裁剪与格式转换（`sharp`）。
     - **网页抓取与浏览器自动化**：HTTP 请求（`axios`）、HTML 解析（`cheerio`）、无头浏览器控制（`playwright-core`）、日期处理（`dayjs`）。
3. **Python 技能环境配方（按模块独立准备）**
   - [skills/http-validation/requirements.txt](../skills/http-validation/requirements.txt)：用于 HTTP 接口请求与 JSON Schema 校验（`requests`、`jsonschema`）。
   - [skills/document-rendering/requirements.txt](../skills/document-rendering/requirements.txt)：用于浏览器页面渲染、PDF 处理与数值图像计算（`playwright`、`Pillow`、`pypdf`、`numpy`、`scipy`）。
4. **面向 AI Agent 的通用工作约定与偏好**
   - [workspace/AGENTS.md](../workspace/AGENTS.md)：约定临时文件、中间产物与最终交付的分目录原则、只读归档保护以及工具/脚本选用规范。
   - [workspace/memory/MEMORY.md](../workspace/memory/MEMORY.md)：记录脱敏后的通用视频制作偏好（配音一致性、自然语速与避免重复镜头）。

> **当前边界说明**：原私有归档中的具体业务技能脚本与模板尚待确认公开授权，当前仓库不含私有业务代码和外部服务凭据。你可以把它当作一个“环境与安全护栏已就绪的干净骨架”，后续确认权限后按技能目录逐个接入。

---

## 二、目录结构一目了然

```text
kangge-agent-platform/
├── README.md                              # 项目总览与快速命令入口
├── docs/
│   ├── usage-guide.md                     # 本文件：通俗功能说明与使用教程
│   └── public-release.md                  # 公开迁移审计说明与原归档来源映射
├── skills/
│   ├── README.md                          # 技能目录索引
│   ├── repository-check/SKILL.md          # 仓库自检技能（完整可用入口）
│   ├── http-validation/requirements.txt   # HTTP 校验技能的 Python 依赖清单
│   └── document-rendering/requirements.txt# 文档渲染技能的 Python 依赖清单
├── workspace/
│   ├── AGENTS.md                          # 给 Agent 看的工作区操作约定
│   ├── memory/MEMORY.md                   # 通用制作偏好
│   ├── package.json                       # Workspace Node.js 依赖清单（14 项）
│   └── package-lock.json                  # 带 SHA-512 摘要的锁定文件（322 项）
├── tools/
│   ├── check_repository.py                # 静态检查与 Git 历史扫描主脚本
│   └── requirements.txt                   # 检查脚本专用依赖（PyYAML==6.0.3）
├── tests/
│   └── test_check_repository.py           # 检查脚本的自动化回归测试
└── .github/workflows/static.yml           # PR 与主干的 GitHub Actions 自动检查
```

---

## 三、怎么使用？（按场景上手）

### 场景 1：第一次拉取仓库，先跑一遍仓库体检

前提：已安装 **Python 3.11+**，并且是**完整克隆**（若使用了 `--depth=1` 浅克隆，先运行 `git fetch --unshallow`）。

```sh
# 1. 创建独立虚拟环境并安装锁定版本的 PyYAML
python3 -m venv .venv
.venv/bin/python -m pip install --no-deps --only-binary=:all: -r tools/requirements.txt

# 2. 运行全仓库静态与历史检查（退出码为 0 即通过）
.venv/bin/python -I tools/check_repository.py

# 3. 运行检查器自身的回归测试
.venv/bin/python -I -m unittest discover -s tests
```

成功时会输出类似如下的 JSON 统计（具体数字随提交略有变化），无报错即表示仓库状态健康：

```json
{"blob": 28, "commit": 4, "config": 3, "partial_modules": 2, "python": 2, "skill_entries": 1, "tag": 0, "tracked": 16, "tree": 22}
```

### 场景 2：安装 Workspace 的 Node.js 工具环境

如果你要在 `workspace/` 中编写或运行处理 Word/PPT/Excel/图表/图片/网页的脚本：

```sh
cd workspace
npm ci --registry=https://registry.npmjs.org --ignore-scripts --no-audit --no-fund
```

- 命令会严格按 `package-lock.json` 中的版本与 SHA-512 摘要安装，并默认禁用生命周期脚本以降低供应链风险。
- 如需自定义 npm 缓存位置，可在运行前通过环境变量 `NPM_CONFIG_CACHE` 指定。
- 如果脚本需要驱动真实浏览器（`playwright-core`），还需在安装后单独下载对应浏览器内核。

### 场景 3：准备 Python 技能依赖环境

两个 Python 依赖目录建议各自使用独立虚拟环境，避免包版本冲突：

```sh
# 示例：准备 HTTP 校验环境
python3 -m venv .venv-http
.venv-http/bin/python -m pip install --only-binary=:all: -r skills/http-validation/requirements.txt

# 示例：准备文档渲染环境
python3 -m venv .venv-render
.venv-render/bin/python -m pip install --only-binary=:all: -r skills/document-rendering/requirements.txt
```

> 使用 `document-rendering` 中的 `playwright` 时，同样需要按需执行 Playwright 浏览器安装命令。

### 场景 4：配合 AI Agent 使用本仓库

- 让 Agent 读取 [workspace/AGENTS.md](../workspace/AGENTS.md) 了解目录分工和脚本编写约定，按需读取 [workspace/memory/MEMORY.md](../workspace/memory/MEMORY.md) 获取制作偏好。
- 需要让 Agent 检查仓库是否合规时，可直接引导它按 [skills/repository-check/SKILL.md](../skills/repository-check/SKILL.md) 执行静态检查并解读结果。

### 场景 5：往仓库里新增一个新的 Skill

当你确认某个业务技能可以公开并准备提交 PR 时，按以下步骤操作即可：

1. 在 `skills/` 下新建目录，例如 `skills/my-new-skill/`。
2. 创建 `skills/my-new-skill/SKILL.md`，顶部必须包含标准 YAML front matter（`name` 和 `description` 均为非空字符串）：

   ```markdown
   ---
   name: my-new-skill
   description: 一句话说明这个技能解决什么问题、何时使用。
   ---

   这里写具体的操作步骤、命令与注意事项。
   ```

3. 如有 Python 依赖，在同目录放置 `requirements.txt`；同时在 [skills/README.md](../skills/README.md) 补充一行索引说明。
4. 提交前在根目录执行 `.venv/bin/python -I tools/check_repository.py`，确保：
   - 没有硬编码密钥、私钥、带密码的连接串或个人联系方式；
   - 没有提交本机用户目录路径、压缩包、数据库或 `.env` 文件；
   - 新增 Python / JSON / YAML / TOML / INI 文件语法全部通过。

---

## 四、常见问题

- **为什么运行检查器提示 `shallow checkout`？**
  检查器需要遍历可达的 Git 历史以防旧提交残留敏感信息。在仓库根目录执行 `git fetch --unshallow` 拉齐历史即可。
- **更新了 `workspace/package.json` 后检查器报错 `dependencies out of sync` 怎么办？**
  需要同步更新 `workspace/package-lock.json`（例如在 `workspace/` 运行 `npm install --package-lock-only --registry=https://registry.npmjs.org`）。
- **可以直接拿这个仓库里的内容开源商用吗？**
  当前仓库尚未指定统一开源许可证，公开复用或再分发前请先与维护者确认许可证类型。
