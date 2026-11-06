# -*- coding: utf-8 -*-
"""Text-to-SQL Agent：自然语言 → SQL → 校验 → 真实执行（失败自动重试）。

设计要点：
1. 表结构不做硬编码，直接反射 SQLite 的 schema，换库即可用；
2. 只信任「执行结果」：生成的 SQL 必须能跑通，且只允许 SELECT；
3. 执行报错时把错误信息回灌给模型重试，而不是直接失败。

依赖：仅标准库 + 可选 sqlglot（装了就用它做语法校验）。
用法：
    export DEEPSEEK_API_KEY=sk-...
    python agent.py "支付总额最高的 5 个城市是哪些？"
"""
import json
import os
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.request

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ecommerce.db")
API_BASE = os.environ.get("TEXT2SQL_API_BASE", "https://api.deepseek.com")
MODEL = os.environ.get("TEXT2SQL_MODEL", "deepseek-chat")

FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|TRUNCATE|ATTACH|PRAGMA|VACUUM)\b", re.I
)

SYSTEM_PROMPT = """你是一名严谨的 SQLite 数据分析师。根据给定的数据库表结构和用户问题，输出**且仅输出**一条可执行的 SQLite 查询语句。

必须遵守：
1. 字段名、表名只能从表结构里选，禁止臆造；
2. 只查询回答问题所需的列，不要 SELECT *；
3. 「已支付订单」指 status IN ('paid','shipped','completed')；
4. 「销售额」按 quantity * unit_price * (1 - discount) 计算；
5. 需要排名或「最近/最高/前 N」时，必须 ORDER BY 并加 LIMIT；
6. 时间字段是 'YYYY-MM-DD' 文本，按字符串比较即可；
7. 只输出 SQL 本身：不要解释，不要 Markdown 代码块，不要分号以外的内容。"""


# ---------------------------------------------------------------- 表结构
def describe_schema(db_path: str = DB_PATH) -> str:
    """反射整个库的表结构，拼成给模型看的文本。"""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    tables = [r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    lines = []
    for t in tables:
        cols = cur.execute(f"PRAGMA table_info({t})").fetchall()
        n = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        cols_txt = ", ".join(f"{c[1]} {c[2]}" for c in cols)
        lines.append(f"- {t}（{n} 行）：{cols_txt}")
    conn.close()
    return "\n".join(lines)


# ---------------------------------------------------------------- 生成
def _chat(messages, api_key, temperature=0.0, timeout=60):
    payload = json.dumps({
        "model": MODEL, "messages": messages, "temperature": temperature, "stream": False,
    }).encode()
    req = urllib.request.Request(
        f"{API_BASE}/v1/chat/completions", data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode())
    return data["choices"][0]["message"]["content"]


def generate_sql(question: str, schema: str, api_key: str, history: list | None = None) -> str:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += history or []
    messages.append({
        "role": "user",
        "content": f"数据库表结构：\n{schema}\n\n问题：{question}\n\n请给出 SQLite 查询：",
    })
    return _chat(messages, api_key)


# ---------------------------------------------------------------- 清洗 / 校验
def clean_sql(text: str) -> str:
    """去掉 Markdown 代码块、多余解释，只留第一条语句。"""
    text = text.strip()
    fence = re.search(r"```(?:sql)?\s*(.+?)```", text, re.S | re.I)
    if fence:
        text = fence.group(1)
    text = text.strip().strip("`").strip()
    # 从第一个 SELECT / WITH 开始
    m = re.search(r"\b(SELECT|WITH)\b", text, re.I)
    if m:
        text = text[m.start():]
    # 只保留到第一个分号
    if ";" in text:
        text = text.split(";")[0] + ";"
    return text.strip()


def validate_sql(sql: str) -> tuple[bool, str]:
    """语法 + 安全校验：只放行单条 SELECT。"""
    if not sql:
        return False, "SQL 为空"
    if FORBIDDEN.search(sql):
        return False, "只允许查询语句，检测到写操作关键字"
    try:
        import sqlglot
        parsed = sqlglot.parse(sql, read="sqlite")
        if len([p for p in parsed if p]) != 1:
            return False, "只允许一条语句"
        if parsed[0].key not in ("select", "with"):
            return False, f"不允许的语句类型：{parsed[0].key}"
    except ImportError:
        pass  # 没装 sqlglot 就退化为正则校验
    except Exception as e:
        return False, f"语法解析失败：{type(e).__name__}: {e}"
    if not re.match(r"^\s*(SELECT|WITH)\b", sql, re.I):
        return False, "必须以 SELECT 或 WITH 开头"
    return True, ""


def execute(conn, sql: str, max_rows: int = 1000):
    cur = conn.execute(sql)
    cols = [d[0] for d in cur.description] if cur.description else []
    rows = cur.fetchmany(max_rows)
    return cols, rows


# ---------------------------------------------------------------- Agent
def ask(question: str, api_key: str | None = None, db_path: str = DB_PATH,
        max_retries: int = 2, verbose: bool = False) -> dict:
    """完整链路：生成 → 清洗 → 校验 → 执行，失败则带错误信息重试。"""
    api_key = api_key or os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise RuntimeError("缺少 API Key：请设置环境变量 DEEPSEEK_API_KEY")

    schema = describe_schema(db_path)
    conn = sqlite3.connect(db_path)
    history = []
    attempts = []

    try:
        for i in range(max_retries + 1):
            raw = generate_sql(question, schema, api_key, history)
            sql = clean_sql(raw)
            ok, reason = validate_sql(sql)
            attempts.append({"sql": sql, "ok": ok, "error": reason})

            if not ok:
                history += [
                    {"role": "assistant", "content": raw},
                    {"role": "user", "content": f"这条 SQL 不能执行：{reason}。请修正后只输出 SQL。"},
                ]
                continue

            try:
                cols, rows = execute(conn, sql)
            except Exception as e:
                attempts[-1]["error"] = f"{type(e).__name__}: {e}"
                history += [
                    {"role": "assistant", "content": raw},
                    {"role": "user", "content": f"执行报错：{e}。请根据表结构修正后只输出 SQL。"},
                ]
                continue

            if verbose:
                print(f"[第 {i + 1} 次尝试成功] {sql}")
            return {"ok": True, "sql": sql, "columns": cols, "rows": rows, "attempts": attempts}
    finally:
        conn.close()

    return {"ok": False, "sql": attempts[-1]["sql"] if attempts else "",
            "error": attempts[-1]["error"] if attempts else "未知错误", "attempts": attempts}


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "支付总额最高的 5 个城市是哪些？"
    result = ask(q, verbose=True)
    print("\nSQL：", result.get("sql"))
    if result["ok"]:
        print("列：", result["columns"])
        for row in result["rows"][:10]:
            print("  ", row)
    else:
        print("失败：", result.get("error"))
