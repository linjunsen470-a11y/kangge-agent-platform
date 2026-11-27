---
name: repository-check
description: 检查本仓库的技能入口、Python 语法、配置格式和 Git 历史中的敏感信息。
---

需要检查本仓库或审阅分支时，从仓库根目录运行。按照根目录 README 准备 Python 环境。

```sh
python -I tools/check_repository.py
```

读取输出中的文件、入口和对象计数。退出码为 0 表示本次规则检查通过。如有命中，按报告的索引或对象位置在本地复核，记录原因类别即可。检查期间无须导入技能、安装业务依赖或访问外部服务。
