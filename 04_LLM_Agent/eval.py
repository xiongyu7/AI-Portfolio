# -*- coding: utf-8 -*-
"""Text-to-SQL 评测：执行准确率（Execution Accuracy）+ 错误分类。

跑法：
    python eval.py --oracle          # 自检：用标准答案当预测，应得 100%
    python eval.py                   # 真实模型（需 DEEPSEEK_API_KEY）
    python eval.py --limit 10        # 只跑前 10 条
    python eval.py --report out.md   # 输出 Markdown 报告

判定口径：只比较**执行结果**，不比较 SQL 字符串——
同一个问题可以有多种写法，结果一致即算对。浮点数统一保留 2 位，结果按多重集比较（忽略行序）。
"""
import argparse
import json
import os
import sqlite3
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "ecommerce.db")
BENCH = os.path.join(HERE, "benchmark.json")

sys.path.insert(0, HERE)


def normalize(rows):
    out = []
    for row in rows:
        vals = []
        for v in row:
            if isinstance(v, float):
                vals.append(round(v, 2))
            elif isinstance(v, str):
                vals.append(v.strip())
            else:
                vals.append(v)
        out.append(tuple(vals))
    return sorted(out)


def run_gold(conn, sql):
    cur = conn.execute(sql)
    return cur.fetchall()


def classify(gold_rows, pred_rows, pred_sql, error=None):
    if error:
        e = str(error).lower()
        if "语法" in str(error) or "syntax" in e:
            return "语法错误"
        return "执行错误"
    if not pred_sql:
        return "未生成 SQL"
    if not pred_rows:
        return "结果为空"
    if len(pred_rows[0]) != len(gold_rows[0]):
        return "列数不一致"
    if normalize(pred_rows) != normalize(gold_rows):
        return "结果不一致"
    return "正确"


def evaluate(predict_fn, limit=None, verbose=False):
    conn = sqlite3.connect(DB)
    bench = json.load(open(BENCH, encoding="utf-8"))
    if limit:
        bench = bench[:limit]

    records = []
    for i, item in enumerate(bench, 1):
        gold_rows = run_gold(conn, item["sql"])
        pred_sql, pred_rows, error = predict_fn(item, conn)

        label = classify(gold_rows, pred_rows, pred_sql, error)
        records.append({
            "id": item["id"], "question": item["question"], "difficulty": item["difficulty"],
            "gold_sql": item["sql"], "pred_sql": pred_sql, "error": error,
            "label": label, "gold_n": len(gold_rows), "pred_n": len(pred_rows or []),
        })
        if verbose:
            mark = "✓" if label == "正确" else "✗"
            print(f"  {mark} [{i:02d}] {item['id']} ({item['difficulty']}) {label}")
    conn.close()
    return records


def summarize(records):
    total = len(records)
    correct = sum(1 for r in records if r["label"] == "正确")
    by_diff = {}
    for d in ("easy", "medium", "hard"):
        subset = [r for r in records if r["difficulty"] == d]
        if subset:
            ok = sum(1 for r in subset if r["label"] == "正确")
            by_diff[d] = (ok, len(subset))
    errors = Counter(r["label"] for r in records if r["label"] != "正确")
    return {"total": total, "correct": correct, "accuracy": correct / total if total else 0,
            "by_diff": by_diff, "errors": errors}


def write_report(records, summ, path, mode):
    lines = [
        "# Text-to-SQL 评测报告", "",
        f"- 评测模式：{mode}",
        f"- 题目数：{summ['total']}",
        f"- 执行准确率：**{summ['accuracy'] * 100:.1f}%**（{summ['correct']}/{summ['total']}）", "",
        "## 分难度", "", "| 难度 | 正确 | 总数 | 准确率 |", "| --- | --- | --- | --- |",
    ]
    for d, (ok, n) in summ["by_diff"].items():
        lines.append(f"| {d} | {ok} | {n} | {ok / n * 100:.1f}% |")

    if summ["errors"]:
        lines += ["", "## 错误分类", "", "| 类型 | 数量 |", "| --- | --- |"]
        for k, v in summ["errors"].most_common():
            lines.append(f"| {k} | {v} |")

    wrong = [r for r in records if r["label"] != "正确"]
    if wrong:
        lines += ["", "## 失败样例", ""]
        for r in wrong[:10]:
            lines += [
                f"### {r['id']}（{r['difficulty']}）{r['label']}", "",
                f"**问题**：{r['question']}", "",
                "```sql", r["gold_sql"], "```", "",
                "预测：", "```sql", (r["pred_sql"] or "-- 空").strip(), "```", "",
            ]
            if r["error"]:
                lines += [f"报错：`{r['error']}`", ""]

    open(path, "w", encoding="utf-8").write("\n".join(lines))
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--oracle", action="store_true", help="用标准答案当作预测，自检评测流程")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--report", default=os.path.join(HERE, "eval_report.md"))
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    if args.oracle:
        def predict(item, conn):
            return item["sql"], run_gold(conn, item["sql"]), None
        mode = "oracle（标准答案自检）"
    else:
        import agent

        def predict(item, conn):
            try:
                res = agent.ask(item["question"], db_path=DB)
            except Exception as e:
                return "", [], f"{type(e).__name__}: {e}"
            if not res["ok"]:
                return res.get("sql", ""), [], res.get("error", "生成失败")
            return res["sql"], res["rows"], None
        mode = f"真实模型（{os.environ.get('TEXT2SQL_MODEL', agent.MODEL)}）"

    records = evaluate(predict, args.limit, args.verbose)
    summ = summarize(records)
    path = write_report(records, summ, args.report, mode)

    print(f"\n准确率 {summ['accuracy'] * 100:.1f}%  ({summ['correct']}/{summ['total']})")
    for d, (ok, n) in summ["by_diff"].items():
        print(f"  {d:<7} {ok}/{n}")
    if summ["errors"]:
        print("  错误类型：", dict(summ["errors"]))
    print("报告：", path)


if __name__ == "__main__":
    main()
