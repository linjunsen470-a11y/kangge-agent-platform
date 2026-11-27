---
name: repository-check
description: 检查本仓库的技能入口、Python 与配置语法和锁文件一致性，并扫描当前文件及 Git 历史中的常见凭据与个人标识。
---

在完整克隆中按[仓库说明](../../README.md#运行静态检查)准备 Python 3.11+ 和固定版本的 PyYAML。然后从仓库根目录运行以下命令。

```sh
.venv/bin/python -I tools/check_repository.py
```

退出码为 0 表示静态规则通过。标准输出列出当前文件、技能、配置和历史对象的计数。错误信息给出类别和可用的位置。敏感路径用索引序号代替，历史问题用 Git 对象 ID 定位。检查过程只读取本地仓库。
