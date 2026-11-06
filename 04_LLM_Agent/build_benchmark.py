# -*- coding: utf-8 -*-
"""定义 50 条 Text-to-SQL 评测题，逐条在真实库上跑通后写入 benchmark.json。

每条包含：id / question（自然语言）/ sql（标准答案）/ difficulty / tags
所有 SQL 都必须是 SQLite 方言，且执行不报错、结果非空（或明确允许为空）。
"""
import json
import os
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "ecommerce.db")
OUT = os.path.join(HERE, "benchmark.json")

PAID = "o.status IN ('paid','shipped','completed')"   # 业务口径：已支付订单

BENCH = [
    # ---------------- easy：单表 / 简单聚合 ----------------
    ("e01", "一共有多少个客户？", "SELECT COUNT(*) AS n FROM customers", "easy", ["count"]),
    ("e02", "一共有多少个商品？", "SELECT COUNT(*) AS n FROM products", "easy", ["count"]),
    ("e03", "状态为已取消（cancelled）的订单有多少笔？",
     "SELECT COUNT(*) AS n FROM orders WHERE status = 'cancelled'", "easy", ["filter"]),
    ("e04", "各个下单渠道的订单数分别是多少？",
     "SELECT channel, COUNT(*) AS n FROM orders GROUP BY channel ORDER BY n DESC", "easy", ["group"]),
    ("e05", "客户等级（level）各有几人？",
     "SELECT level, COUNT(*) AS n FROM customers GROUP BY level ORDER BY n DESC", "easy", ["group"]),
    ("e06", "所有支付记录的平均金额是多少？",
     "SELECT ROUND(AVG(amount), 2) AS avg_amount FROM payments", "easy", ["avg"]),
    ("e07", "打 5 星的评论有多少条？",
     "SELECT COUNT(*) AS n FROM reviews WHERE rating = 5", "easy", ["filter"]),
    ("e08", "注册城市为北京的客户有多少人？",
     "SELECT COUNT(*) AS n FROM customers WHERE city = '北京'", "easy", ["filter"]),
    ("e09", "当前在售（on_sale）的商品有多少个？",
     "SELECT COUNT(*) AS n FROM products WHERE status = 'on_sale'", "easy", ["filter"]),
    ("e10", "所有评论的平均评分是多少？",
     "SELECT ROUND(AVG(rating), 2) AS avg_rating FROM reviews", "easy", ["avg"]),
    ("e11", "不同支付方式的支付笔数分别是多少？",
     "SELECT method, COUNT(*) AS n FROM payments GROUP BY method ORDER BY n DESC", "easy", ["group"]),
    ("e12", "各快递公司承运的包裹数量分别是多少？",
     "SELECT carrier, COUNT(*) AS n FROM shipments GROUP BY carrier ORDER BY n DESC", "easy", ["group"]),
    ("e13", "2024 年一共产生了多少笔订单？",
     "SELECT COUNT(*) AS n FROM orders WHERE order_date >= '2024-01-01' AND order_date < '2025-01-01'", "easy", ["time"]),
    ("e14", "所有商品的平均售价是多少？",
     "SELECT ROUND(AVG(price), 2) AS avg_price FROM products", "easy", ["avg"]),
    ("e15", "评论内容为「包装破损」的记录有多少条？",
     "SELECT COUNT(*) AS n FROM reviews WHERE content = '包装破损'", "easy", ["filter"]),
    ("e16", "各订单状态的订单数分别是多少？",
     "SELECT status, COUNT(*) AS n FROM orders GROUP BY status ORDER BY n DESC", "easy", ["group"]),

    # ---------------- medium：JOIN / 分组 ----------------
    ("m01", "每个品类下有多少个商品？",
     "SELECT c.name AS category, COUNT(p.id) AS n FROM categories c "
     "JOIN products p ON p.category_id = c.id GROUP BY c.id ORDER BY n DESC", "medium", ["join", "group"]),
    ("m02", "下单次数最多的 10 位客户是谁？",
     "SELECT customer_id, COUNT(*) AS n FROM orders GROUP BY customer_id ORDER BY n DESC, customer_id LIMIT 10",
     "medium", ["group", "topn"]),
    ("m03", "按支付金额统计，销售额最高的 10 个商品是哪些？",
     "SELECT p.name, ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount)), 2) AS revenue "
     "FROM order_items oi JOIN orders o ON o.id = oi.order_id JOIN payments pa ON pa.order_id = o.id "
     "JOIN products p ON p.id = oi.product_id GROUP BY p.id ORDER BY revenue DESC, p.id LIMIT 10",
     "medium", ["join", "group", "topn"]),
    ("m04", "每个品类的销售额（按支付金额）分别是多少？",
     "SELECT c.name AS category, ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount)), 2) AS revenue "
     "FROM order_items oi JOIN orders o ON o.id = oi.order_id JOIN payments pa ON pa.order_id = o.id "
     "JOIN products p ON p.id = oi.product_id JOIN categories c ON c.id = p.category_id "
     "GROUP BY c.id ORDER BY revenue DESC", "medium", ["join", "group"]),
    ("m05", "2025 年每个月的订单数是多少？",
     "SELECT substr(order_date, 1, 7) AS month, COUNT(*) AS n FROM orders "
     "WHERE order_date >= '2025-01-01' AND order_date < '2026-01-01' GROUP BY month ORDER BY month",
     "medium", ["time", "group"]),
    ("m06", "各个下单渠道的平均支付金额是多少？",
     "SELECT o.channel, ROUND(AVG(pa.amount), 2) AS avg_amount FROM payments pa "
     "JOIN orders o ON o.id = pa.order_id GROUP BY o.channel ORDER BY avg_amount DESC",
     "medium", ["join", "avg"]),
    ("m07", "还没有支付记录的订单有多少笔？",
     "SELECT COUNT(*) AS n FROM orders o LEFT JOIN payments pa ON pa.order_id = o.id WHERE pa.id IS NULL",
     "medium", ["join", "null"]),
    ("m08", "支付总额最高的 5 个城市是哪些？",
     "SELECT c.city, ROUND(SUM(pa.amount), 2) AS total FROM payments pa "
     "JOIN orders o ON o.id = pa.order_id JOIN customers c ON c.id = o.customer_id "
     "GROUP BY c.city ORDER BY total DESC LIMIT 5", "medium", ["join", "group", "topn"]),
    ("m09", "评论数最多的 10 个商品是哪些？",
     "SELECT p.name, COUNT(r.id) AS n FROM reviews r JOIN products p ON p.id = r.product_id "
     "GROUP BY p.id ORDER BY n DESC, p.id LIMIT 10", "medium", ["join", "topn"]),
    ("m10", "不同客户等级的平均支付金额分别是多少？",
     "SELECT c.level, ROUND(AVG(pa.amount), 2) AS avg_amount FROM payments pa "
     "JOIN orders o ON o.id = pa.order_id JOIN customers c ON c.id = o.customer_id "
     "GROUP BY c.level ORDER BY avg_amount DESC", "medium", ["join", "avg"]),
    ("m11", "2026 年每个月的支付总额是多少？",
     "SELECT substr(pa.paid_at, 1, 7) AS month, ROUND(SUM(pa.amount), 2) AS total FROM payments pa "
     "WHERE pa.paid_at >= '2026-01-01' AND pa.paid_at < '2027-01-01' GROUP BY month ORDER BY month",
     "medium", ["time", "sum"]),
    ("m12", "退款订单（refunded）占全部订单的比例是多少？",
     "SELECT ROUND(100.0 * SUM(CASE WHEN status = 'refunded' THEN 1 ELSE 0 END) / COUNT(*), 2) AS pct FROM orders",
     "medium", ["case", "ratio"]),
    ("m13", "各快递公司的平均送达天数（下单到签收）是多少？",
     "SELECT s.carrier, ROUND(AVG(julianday(s.delivered_at) - julianday(o.order_date)), 2) AS avg_days "
     "FROM shipments s JOIN orders o ON o.id = s.order_id GROUP BY s.carrier ORDER BY avg_days",
     "medium", ["join", "date"]),
    ("m14", "销量（件数）最高的 5 个商品是哪些？",
     "SELECT p.name, SUM(oi.quantity) AS qty FROM order_items oi JOIN products p ON p.id = oi.product_id "
     "GROUP BY p.id ORDER BY qty DESC, p.id LIMIT 5", "medium", ["join", "topn"]),
    ("m15", "每个品类的商品平均售价是多少？",
     "SELECT c.name AS category, ROUND(AVG(p.price), 2) AS avg_price FROM products p "
     "JOIN categories c ON c.id = p.category_id GROUP BY c.id ORDER BY avg_price DESC",
     "medium", ["join", "avg"]),
    ("m16", "每个订单平均包含多少件商品？",
     "SELECT ROUND(AVG(cnt), 2) AS avg_items FROM (SELECT order_id, SUM(quantity) AS cnt FROM order_items GROUP BY order_id)",
     "medium", ["subquery", "avg"]),
    ("m17", "各渠道的退款订单数分别是多少？",
     "SELECT channel, COUNT(*) AS n FROM orders WHERE status = 'refunded' GROUP BY channel ORDER BY n DESC",
     "medium", ["filter", "group"]),
    ("m18", "2025 年注册的客户有多少人？",
     "SELECT COUNT(*) AS n FROM customers WHERE signup_date >= '2025-01-01' AND signup_date < '2026-01-01'",
     "medium", ["time"]),

    # ---------------- hard：子查询 / 窗口函数 ----------------
    ("h01", "支付总额最高的客户叫什么名字，总额是多少？",
     "SELECT c.name, ROUND(SUM(pa.amount), 2) AS total FROM payments pa "
     "JOIN orders o ON o.id = pa.order_id JOIN customers c ON c.id = o.customer_id "
     "GROUP BY c.id ORDER BY total DESC, c.id LIMIT 1", "hard", ["join", "topn"]),
    ("h02", "下单次数达到 10 次及以上的客户有多少人？",
     "SELECT COUNT(*) AS n FROM (SELECT customer_id FROM orders GROUP BY customer_id HAVING COUNT(*) >= 10)",
     "hard", ["subquery", "having"]),
    ("h03", "每个品类中销量最高的商品是哪个？",
     "SELECT category, name, qty FROM (SELECT c.name AS category, p.name, SUM(oi.quantity) AS qty, "
     "ROW_NUMBER() OVER (PARTITION BY c.id ORDER BY SUM(oi.quantity) DESC, p.id) AS rn "
     "FROM order_items oi JOIN products p ON p.id = oi.product_id JOIN categories c ON c.id = p.category_id "
     "GROUP BY c.id, p.id) WHERE rn = 1 ORDER BY category", "hard", ["window"]),
    ("h04", "每位客户最近一次下单的日期是什么时候？（只列出有订单的客户）",
     "SELECT c.id, c.name, MAX(o.order_date) AS last_order FROM customers c "
     "JOIN orders o ON o.customer_id = c.id GROUP BY c.id ORDER BY last_order DESC, c.id LIMIT 20",
     "hard", ["group", "max"]),
    ("h05", "从来没有下过单的客户有多少人？",
     "SELECT COUNT(*) AS n FROM customers c LEFT JOIN orders o ON o.customer_id = c.id WHERE o.id IS NULL",
     "hard", ["join", "null"]),
    ("h06", "各城市的复购率（下单 2 次及以上的客户占比）是多少？",
     "SELECT c.city, ROUND(100.0 * SUM(CASE WHEN t.n >= 2 THEN 1 ELSE 0 END) / COUNT(*), 2) AS repeat_rate "
     "FROM customers c LEFT JOIN (SELECT customer_id, COUNT(*) AS n FROM orders GROUP BY customer_id) t "
     "ON t.customer_id = c.id GROUP BY c.city ORDER BY repeat_rate DESC", "hard", ["subquery", "ratio"]),
    ("h07", "哪些渠道的平均支付金额高于全站平均？",
     "SELECT channel, ROUND(avg_amount, 2) AS avg_amount FROM ("
     "SELECT o.channel AS channel, AVG(pa.amount) AS avg_amount FROM payments pa "
     "JOIN orders o ON o.id = pa.order_id GROUP BY o.channel) "
     "WHERE avg_amount > (SELECT AVG(amount) FROM payments) ORDER BY avg_amount DESC", "hard", ["subquery"]),
    ("h08", "各品类的销售额占总销售额的比例分别是多少？",
     "SELECT c.name AS category, ROUND(100.0 * SUM(oi.quantity * oi.unit_price * (1 - oi.discount)) / "
     "(SELECT SUM(quantity * unit_price * (1 - discount)) FROM order_items), 2) AS pct "
     "FROM order_items oi JOIN products p ON p.id = oi.product_id JOIN categories c ON c.id = p.category_id "
     "GROUP BY c.id ORDER BY pct DESC", "hard", ["window", "ratio"]),
    ("h09", "支付金额与订单明细合计金额不一致的订单有多少笔？（差异超过 0.01 元）",
     "SELECT COUNT(*) AS n FROM (SELECT o.id, pa.amount AS paid, "
     "SUM(oi.quantity * oi.unit_price * (1 - oi.discount)) AS calc FROM orders o "
     "JOIN payments pa ON pa.order_id = o.id JOIN order_items oi ON oi.order_id = o.id "
     "GROUP BY o.id HAVING ABS(pa.amount - SUM(oi.quantity * oi.unit_price * (1 - oi.discount))) > 0.01)",
     "hard", ["checksum"]),
    ("h10", "平均评分最低的商品是哪一个？它的评论数是多少？",
     "SELECT p.name, ROUND(AVG(r.rating), 2) AS avg_rating, COUNT(*) AS n FROM reviews r "
     "JOIN products p ON p.id = r.product_id GROUP BY p.id "
     "ORDER BY avg_rating ASC, p.id LIMIT 1", "hard", ["having", "topn"]),
    ("h11", "每个月有多少位不同的客户下过单？",
     "SELECT substr(order_date, 1, 7) AS month, COUNT(DISTINCT customer_id) AS customers FROM orders "
     "GROUP BY month ORDER BY month", "hard", ["distinct", "time"]),
    ("h12", "客户首次购买与第二次购买的平均间隔天数是多少？",
     "SELECT ROUND(AVG(gap), 2) AS avg_days FROM (SELECT customer_id, "
     "julianday(order_date) - julianday(LAG(order_date) OVER (PARTITION BY customer_id ORDER BY order_date)) AS gap "
     "FROM orders) WHERE gap IS NOT NULL", "hard", ["window", "date"]),
    ("h13", "各客户等级的平均订单笔数是多少？",
     "SELECT c.level, ROUND(AVG(t.n), 2) AS avg_orders FROM customers c "
     "LEFT JOIN (SELECT customer_id, COUNT(*) AS n FROM orders GROUP BY customer_id) t ON t.customer_id = c.id "
     "GROUP BY c.level ORDER BY avg_orders DESC", "hard", ["subquery", "avg"]),
    ("h14", "支付总额最高的 3 个城市中，销量最高的商品是哪个？",
     "SELECT p.name, SUM(oi.quantity) AS qty FROM order_items oi "
     "JOIN orders o ON o.id = oi.order_id JOIN payments pa ON pa.order_id = o.id "
     "JOIN customers c ON c.id = o.customer_id JOIN products p ON p.id = oi.product_id "
     "WHERE c.city IN (SELECT c2.city FROM payments pa2 JOIN orders o2 ON o2.id = pa2.order_id "
     "JOIN customers c2 ON c2.id = o2.customer_id GROUP BY c2.city ORDER BY SUM(pa2.amount) DESC LIMIT 3) "
     "GROUP BY p.id ORDER BY qty DESC, p.id LIMIT 1", "hard", ["subquery", "topn"]),
    ("h15", "下单次数最多的前 3 位客户一共贡献了多少件商品？",
     "SELECT SUM(oi.quantity) AS qty FROM order_items oi JOIN orders o ON o.id = oi.order_id "
     "WHERE o.customer_id IN (SELECT customer_id FROM orders GROUP BY customer_id ORDER BY COUNT(*) DESC LIMIT 3)",
     "hard", ["subquery", "sum"]),
    ("h16", "每个月的新客户数与当月订单数相比，哪个月的订单客户比最高？",
     "SELECT substr(o.order_date, 1, 7) AS month, COUNT(DISTINCT o.customer_id) AS buyers, "
     "COUNT(*) AS orders, ROUND(1.0 * COUNT(*) / COUNT(DISTINCT o.customer_id), 3) AS ratio FROM orders o "
     "GROUP BY month ORDER BY ratio DESC LIMIT 1", "hard", ["ratio", "time"]),
]


def main() -> None:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    ok, bad = [], []
    for qid, question, sql, diff, tags in BENCH:
        try:
            cur = conn.execute(sql)
            rows = cur.fetchall()
            if not rows:
                bad.append((qid, "结果为空", sql))
                continue
            ok.append({"id": qid, "question": question, "sql": sql, "difficulty": diff, "tags": tags})
        except Exception as e:
            bad.append((qid, f"{type(e).__name__}: {e}", sql))
    conn.close()

    print(f"通过 {len(ok)} / {len(BENCH)}")
    for qid, err, sql in bad:
        print(f"  !! {qid}: {err}")
        print(f"     {sql[:120]}")

    if not bad:
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(ok, f, ensure_ascii=False, indent=2)
        print(f"已写入 {OUT}")


if __name__ == "__main__":
    main()
