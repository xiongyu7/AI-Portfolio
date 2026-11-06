# -*- coding: utf-8 -*-
"""生成一个接近真实业务规模的电商库（SQLite），供 Text-to-SQL 评测使用。

用法：
    python build_db.py            # 生成 ecommerce.db（约 8 MB，不提交到 Git）
    python build_db.py --force    # 覆盖已存在的库

规模：8 张表，订单 2 万单、订单明细 4.5 万行，时间跨度 2024-01 至 2026-10。
"""
import argparse
import os
import random
import sqlite3
from datetime import date, timedelta

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ecommerce.db")
SEED = 20261106

CITIES = ["北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", "南京", "西安", "重庆"]
CHANNELS = ["app", "h5", "mini_program", "offline"]
ORDER_STATUS = ["created", "paid", "shipped", "completed", "cancelled", "refunded"]
PAY_METHODS = ["alipay", "wechat", "card", "balance"]
CARRIERS = ["SF", "YTO", "ZTO", "JD", "EMS"]
LEVELS = ["bronze", "silver", "gold", "platinum"]
CATEGORIES = [
    (1, "数码", None), (2, "手机", 1), (3, "笔记本", 1), (4, "耳机", 1),
    (5, "服饰", None), (6, "男装", 5), (7, "女装", 5), (8, "鞋靴", 5),
    (9, "家居", None), (10, "厨房", 9), (11, "床品", 9),
    (12, "美妆", None), (13, "护肤", 12), (14, "彩妆", 12),
    (15, "食品", None), (16, "零食", 15), (17, "饮料", 15),
]
NAMES = ["小米", "华为", "苹果", "联想", "戴森", "海尔", "李宁", "安踏", "优衣库", "珀莱雅", "三只松鼠", "农夫山泉"]
SURNAMES = list("王李张刘陈杨黄赵吴周徐孙马朱胡郭何高林罗郑梁谢宋唐许韩冯邓曹彭曾肖田董袁潘于蒋蔡余杜叶程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾夏韦付方白邹孟熊秦邱江尹薛闫段雷侯龙史陶黎贺顾毛郝龚邵万钱严覃武戴莫孔向汤")


def build(force: bool) -> None:
    if os.path.exists(DB):
        if not force:
            print(f"数据库已存在：{DB}\n如需重建请加 --force")
            return
        os.remove(DB)

    rnd = random.Random(SEED)
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.executescript(
        """
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY, name TEXT, city TEXT, signup_date TEXT, level TEXT
        );
        CREATE TABLE categories (
            id INTEGER PRIMARY KEY, name TEXT, parent_id INTEGER
        );
        CREATE TABLE products (
            id INTEGER PRIMARY KEY, name TEXT, category_id INTEGER,
            price REAL, cost REAL, launch_date TEXT, status TEXT
        );
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY, customer_id INTEGER, order_date TEXT,
            status TEXT, channel TEXT
        );
        CREATE TABLE order_items (
            id INTEGER PRIMARY KEY, order_id INTEGER, product_id INTEGER,
            quantity INTEGER, unit_price REAL, discount REAL
        );
        CREATE TABLE payments (
            id INTEGER PRIMARY KEY, order_id INTEGER, paid_at TEXT,
            method TEXT, amount REAL
        );
        CREATE TABLE shipments (
            id INTEGER PRIMARY KEY, order_id INTEGER, shipped_at TEXT,
            delivered_at TEXT, carrier TEXT
        );
        CREATE TABLE reviews (
            id INTEGER PRIMARY KEY, product_id INTEGER, customer_id INTEGER,
            rating INTEGER, created_at TEXT, content TEXT
        );
        """
    )

    cur.executemany("INSERT INTO categories VALUES (?,?,?)", CATEGORIES)

    # ---------- 客户 ----------
    customers = []
    for cid in range(1, 2001):
        signup = date(2023, 1, 1) + timedelta(days=rnd.randint(0, 1100))
        customers.append((
            cid, rnd.choice(SURNAMES) + rnd.choice("伟芳娜敏静秀英华慧巧美娟"),
            rnd.choice(CITIES), signup.isoformat(), rnd.choices(LEVELS, weights=[50, 30, 15, 5])[0],
        ))
    cur.executemany("INSERT INTO customers VALUES (?,?,?,?,?)", customers)

    # ---------- 商品 ----------
    products = []
    for pid in range(1, 801):
        cat = rnd.choice(CATEGORIES)[0]
        price = round(rnd.uniform(19, 6999), 2)
        launch = date(2022, 6, 1) + timedelta(days=rnd.randint(0, 1500))
        products.append((
            pid, f"{rnd.choice(NAMES)}{cat}-{pid}", cat, price,
            round(price * rnd.uniform(0.45, 0.75), 2), launch.isoformat(),
            rnd.choices(["on_sale", "off_shelf"], weights=[85, 15])[0],
        ))
    cur.executemany("INSERT INTO products VALUES (?,?,?,?,?,?,?)", products)
    price_of = {p[0]: p[3] for p in products}

    # ---------- 订单 / 明细 / 支付 / 物流 ----------
    start = date(2024, 1, 1)
    total_days = (date(2026, 10, 31) - start).days
    orders, items, payments, shipments = [], [], [], []
    item_id = 0
    for oid in range(1, 20001):
        # 让订单量随时间缓增，贴近真实业务
        day_offset = int(total_days * (rnd.random() ** 0.85))
        od = start + timedelta(days=day_offset)
        status = rnd.choices(ORDER_STATUS, weights=[10, 15, 15, 45, 10, 5])[0]
        orders.append((oid, rnd.randint(1, 2000), od.isoformat(), status, rnd.choice(CHANNELS)))

        order_total = 0.0
        for _ in range(rnd.randint(1, 4)):
            item_id += 1
            pid = rnd.randint(1, 800)
            qty = rnd.randint(1, 4)
            unit = price_of[pid]
            disc = rnd.choice([0, 0, 0, 0.05, 0.1, 0.2])
            order_total += qty * unit * (1 - disc)
            items.append((item_id, oid, pid, qty, unit, disc))

        if status in ("paid", "shipped", "completed", "refunded"):
            payments.append((
                len(payments) + 1, oid, (od + timedelta(hours=rnd.randint(1, 48))).isoformat(),
                rnd.choice(PAY_METHODS), round(order_total, 2),
            ))
        if status in ("shipped", "completed"):
            shipped = od + timedelta(days=rnd.randint(1, 3))
            shipments.append((
                len(shipments) + 1, oid, shipped.isoformat(),
                (shipped + timedelta(days=rnd.randint(1, 6))).isoformat(),
                rnd.choice(CARRIERS),
            ))

    cur.executemany("INSERT INTO orders VALUES (?,?,?,?,?)", orders)
    cur.executemany("INSERT INTO order_items VALUES (?,?,?,?,?,?)", items)
    cur.executemany("INSERT INTO payments VALUES (?,?,?,?,?)", payments)
    cur.executemany("INSERT INTO shipments VALUES (?,?,?,?,?)", shipments)

    # ---------- 评论 ----------
    reviews = []
    for rid in range(1, 15001):
        reviews.append((
            rid, rnd.randint(1, 800), rnd.randint(1, 2000), rnd.choices([1, 2, 3, 4, 5], weights=[5, 5, 15, 35, 40])[0],
            (start + timedelta(days=rnd.randint(0, total_days))).isoformat(),
            rnd.choice(["很好用", "质量一般", "物流很快", "和描述一致", "包装破损", "性价比高"]),
        ))
    cur.executemany("INSERT INTO reviews VALUES (?,?,?,?,?,?)", reviews)

    cur.executescript(
        """
        CREATE INDEX idx_orders_date ON orders(order_date);
        CREATE INDEX idx_orders_customer ON orders(customer_id);
        CREATE INDEX idx_items_order ON order_items(order_id);
        CREATE INDEX idx_items_product ON order_items(product_id);
        """
    )
    conn.commit()

    stats = {t: cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
             for t in ("customers", "categories", "products", "orders", "order_items", "payments", "shipments", "reviews")}
    conn.close()

    size_mb = os.path.getsize(DB) / 1024 / 1024
    print(f"已生成 {DB}（{size_mb:.1f} MB）")
    for k, v in stats.items():
        print(f"  {k:<12} {v:>7,} 行")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    build(ap.parse_args().force)
