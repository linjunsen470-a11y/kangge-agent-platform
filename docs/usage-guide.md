# 使用指南

从仓库根目录执行下列命令，按需安装对应模块。检查仓库本身只需准备[静态检查环境](../README.md#运行静态检查)。

## Workspace 依赖

按锁文件安装 Node.js 工具包，并禁用生命周期脚本。

```sh
cd workspace
npm ci --registry=https://registry.npmjs.org --ignore-scripts --no-audit --no-fund
```

修改 `workspace/package.json` 的依赖后，在 `workspace/` 运行 `npm install --package-lock-only --ignore-scripts --registry=https://registry.npmjs.org`，将两份清单一同提交。

## Python 模块

从仓库根目录为需要的模块建立独立环境。HTTP 请求和 JSON Schema 校验使用以下环境。

```sh
python3 -m venv skills/http-validation/.venv
skills/http-validation/.venv/bin/python -m pip install --only-binary=:all: -r skills/http-validation/requirements.txt
```

页面渲染、图像和 PDF 处理使用以下环境。

```sh
python3 -m venv skills/document-rendering/.venv
skills/document-rendering/.venv/bin/python -m pip install --only-binary=:all: -r skills/document-rendering/requirements.txt
```

用 Playwright 启动浏览器时，还需为所用版本安装对应的浏览器内核。

## 新增技能

在 `skills/<名称>/SKILL.md` 的 YAML 文件头填写非空字符串 `name` 和 `description`。仅提供依赖的目录使用 `requirements.txt`。更新[技能索引](../skills/README.md)，核实公开授权，并在提交前运行[仓库检查](../README.md#运行静态检查)。
