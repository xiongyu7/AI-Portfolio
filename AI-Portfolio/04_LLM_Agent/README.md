# 04 · LLM Agent：让大模型写 SQL 并真实执行

这个项目要解决一个很具体的问题：**用自然语言查数据库**。

流程是：问题 → 表结构塞进 Prompt → 大模型生成 SQL → 清理 Markdown → 交给 SQLite 真执行 → 拿回结果。

关键点在于：**大模型只负责"写"，不负责"对"**。SQL 到底对不对，必须落到真实数据库上跑一遍才知道。

## 文件

| 文件 | 说明 |
| --- | --- |
| `01_sql_basics.ipynb` | SQL 基础：建库、条件查询、聚合（已执行） |
| `02_text2sql_agent.ipynb` | Text-to-SQL：Prompt 设计 + 生成 + 执行验证 |
| `company.db` | 5 条员工记录的 SQLite 库，由 01 生成 |

## 运行

```bash
pip install openai pandas

# 先跑 01 生成 company.db，再跑 02
$env:DEEPSEEK_API_KEY = "sk-..."   # PowerShell；macOS/Linux 用 export
jupyter lab
```

## 输出示例

问题："帮我查一下研发部工资大于 15000 的人有哪些？"

模型生成：

```sql
SELECT id, name, department, salary
FROM employees
WHERE department = '研发部' AND salary > 15000;
```

真实执行结果：

| id | name | department | salary |
| --- | --- | --- | --- |
| 2 | 李四 | 研发部 | 18000 |

## 一个安全提醒

生产环境让模型直接生成 SQL 是有风险的——它完全可能写出 `DROP TABLE` 或者扫全表。至少要加三道闸：

1. 用只读账号连接数据库；
2. 只放行 `SELECT`，用 `sqlglot` 之类做语法树校验；
3. 强制 `LIMIT`，防止一次查出几百万行。

## 踩过的坑

最初把 API Key 直接写在 `client = OpenAI(api_key="sk-...")` 里，传到 GitHub 就等于把 Key 公开了。现在改成从环境变量读取，仓库里不留任何密钥。
