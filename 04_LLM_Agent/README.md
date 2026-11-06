# 04 · LLM Agent：Text-to-SQL 与可验证的评测

> 让大模型把自然语言问题翻译成 SQL，并且**证明**它翻译对了。

重点不在"接个大模型 API 生成 SQL"——那件事 20 行代码就能做完。难点在于：**你怎么知道它写对了？**

这个项目因此分三层：

1. **真实规模的数据**：8 张表、2 万订单、5 万条订单明细，不是 6 条玩具数据；
2. **可复现的链路**：表结构反射 → Prompt → 清洗 → 语法/安全校验 → 真实执行 → 报错回灌重试；
3. **可量化的评测**：50 道题 + 标准答案，用**执行结果**比对，而不比对 SQL 字符串。

## 目录

```text
04_LLM_Agent/
├── build_db.py          # 生成 ecommerce.db（8 表，约 5 MB，不提交到 Git）
├── build_benchmark.py   # 50 道题的标准答案，逐条跑通后写入 benchmark.json
├── benchmark.json       # 评测集：问题 + 标准 SQL + 难度 + 标签
├── agent.py             # Agent 主体：生成、清洗、校验、执行、重试
├── eval.py              # 评测：执行准确率 + 错误分类 + Markdown 报告
├── tests.py             # 16 个单元测试（不依赖网络）
└── tutorial/            # 最初的学习版：SQL 基础 + 简化版 Text-to-SQL
```

## 快速开始

```bash
pip install sqlglot                 # 可选：装了才有完整语法校验
python build_db.py                  # 建库
python build_benchmark.py           # 校验 50 道标准答案能否跑通

python -m unittest tests -v         # 16 个测试
python eval.py --oracle             # 评测流程自检：应得 100%

export DEEPSEEK_API_KEY=sk-...      # PowerShell: $env:DEEPSEEK_API_KEY="sk-..."
python eval.py                      # 真实模型评测
python agent.py "支付总额最高的 5 个城市是哪些？"
```

## 评测设计

- **50 道题**：easy 16 / medium 18 / hard 16，覆盖单表过滤、聚合、多表 JOIN、时间窗口、Top-N、子查询和窗口函数；
- **判定口径是执行准确率（Execution Accuracy）**：同一个问题可以有多种 SQL 写法，只比结果集，结果一致即算对——浮点数保留 2 位，忽略行序；
- **错误分五类**：未生成 SQL / 语法错误 / 执行错误 / 结果为空 / 结果不一致。分类比总分有用：知道错在哪，才知道该改 Prompt 还是改 schema 描述。

评测流程本身已经通过自检（用标准答案当预测，50/50）。真实模型的成绩需要你自己的 API Key 跑出来——我没有把没有实测的数字写进这里。

## 几个设计取舍

**为什么用执行结果比对，而不是比对 SQL 文本？**
`SELECT a FROM t WHERE x>1` 和 `SELECT a FROM t WHERE 1<x` 是同一件事。SQL 字符串比对会把正确答案判错。

**为什么要把表结构反射出来，而不是写死在 Prompt 里？**
换一个库就要改 Prompt，这种项目没法复用。`describe_schema()` 直接读 `sqlite_master` 和 `PRAGMA table_info`，连同每张表的行数一起给模型——行数能帮助模型判断"要不要加 LIMIT"。

**为什么要做重试？**
模型第一次写错字段名是常态。把 `no such column: xxx` 回灌给它，第二次通常就对了。这比"报错直接失败"更接近真实产品的做法。

## 安全边界

生产环境不能让模型直接对数据库执行 SQL。这个项目里做了三层限制，README 里也写明：

1. 正则 + `sqlglot` 双重校验，只放行单条 `SELECT` / `WITH`；
2. 执行前拦截 `DROP / DELETE / UPDATE / INSERT` 等关键字；
3. 查询结果截断到 1000 行。

再往前一步应该是：只读账号、独立 schema、审计日志。

## 技术栈

`Python` · `SQLite` · `DeepSeek API（OpenAI 兼容）` · `sqlglot` · `unittest`
