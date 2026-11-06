# -*- coding: utf-8 -*-
"""针对 agent.py / eval.py 里的纯逻辑做单元测试（不依赖网络和 API Key）。

运行：
    python -m unittest tests -v
"""
import unittest

import agent
import eval as ev


class TestCleanSql(unittest.TestCase):
    def test_strip_markdown_fence(self):
        raw = "```sql\nSELECT COUNT(*) FROM orders;\n```"
        self.assertEqual(agent.clean_sql(raw), "SELECT COUNT(*) FROM orders;")

    def test_strip_prose(self):
        raw = "好的，这是一个查询：\nSELECT name FROM products LIMIT 5;"
        self.assertTrue(agent.clean_sql(raw).startswith("SELECT name"))

    def test_keep_first_statement(self):
        raw = "SELECT 1; DROP TABLE orders;"
        self.assertEqual(agent.clean_sql(raw), "SELECT 1;")

    def test_with_clause_preserved(self):
        raw = "WITH t AS (SELECT 1) SELECT * FROM t"
        self.assertTrue(agent.clean_sql(raw).startswith("WITH t"))


class TestValidateSql(unittest.TestCase):
    def test_accept_select(self):
        ok, _ = agent.validate_sql("SELECT id FROM orders LIMIT 10")
        self.assertTrue(ok)

    def test_reject_drop(self):
        ok, reason = agent.validate_sql("DROP TABLE orders")
        self.assertFalse(ok)
        self.assertIn("写操作", reason)

    def test_reject_delete(self):
        ok, _ = agent.validate_sql("DELETE FROM orders")
        self.assertFalse(ok)

    def test_reject_multi_statement(self):
        ok, _ = agent.validate_sql("SELECT 1; SELECT 2")
        self.assertFalse(ok)

    def test_reject_garbage(self):
        ok, _ = agent.validate_sql("这不是 SQL")
        self.assertFalse(ok)


class TestCompare(unittest.TestCase):
    def test_normalize_ignores_row_order(self):
        self.assertEqual(ev.normalize([(1, "a"), (2, "b")]), ev.normalize([(2, "b"), (1, "a")]))

    def test_normalize_rounds_floats(self):
        self.assertEqual(ev.normalize([(3.14159,)]), ev.normalize([(3.14,)]))

    def test_classify_correct(self):
        self.assertEqual(ev.classify([(1,)], [(1,)], "SELECT 1"), "正确")

    def test_classify_empty(self):
        self.assertEqual(ev.classify([(1,)], [], "SELECT 1"), "结果为空")

    def test_classify_column_mismatch(self):
        self.assertEqual(ev.classify([(1, 2)], [(1,)], "SELECT 1"), "列数不一致")

    def test_classify_mismatch(self):
        self.assertEqual(ev.classify([(1,)], [(2,)], "SELECT 2"), "结果不一致")

    def test_classify_error(self):
        self.assertEqual(ev.classify([(1,)], [], "SELECT x", "no such column: x"), "执行错误")


if __name__ == "__main__":
    unittest.main()
