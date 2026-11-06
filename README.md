# Hi there, I'm 熊宇 👋

> 正在寻找 **AI 应用开发 / 数据分析** 岗位机会。

2027 届，从表格数据建模起步，现在在做"模型怎么变成能用的东西"——
用 FastAPI 把模型包成接口，用大模型把自然语言变成能真实执行的查询。

## 🛠 我的技能栈

- **语言与工具**：Python、SQL、Git、Jupyter
- **数据分析**：Pandas、NumPy、Matplotlib
- **机器学习**：scikit-learn（分类、回归、交叉验证、特征工程）
- **AI 应用开发**：FastAPI、大模型 API 调用（DeepSeek / OpenAI 兼容接口）

## 📝 我的项目

### 1. [基于 LLM 的智能 SQL 数据分析 Agent](04_LLM_Agent/)

自然语言 → 大模型生成 SQL → 清洗 → 交给 SQLite **真实执行** → 返回结果表。

关键不在"让模型写 SQL"，而在**验证**：搭了 50 道题的评测集（easy / medium / hard = 16 / 18 / 16），用**执行结果**而非 SQL 字符串比对，输出执行准确率和五类错误分布。底层是 8 张表、2 万订单的真实规模数据库。

`Python` · `DeepSeek API` · `SQLite` · `sqlglot` · `unittest`

### 2. [垃圾邮件分类 API 服务](03_Spam_API/)

`CountVectorizer` + `MultinomialNB` 做文本分类，用 FastAPI 封装成 `/predict` 接口，自带 Swagger 文档页。

`Python` · `scikit-learn` · `FastAPI`

### 3. [泰坦尼克号生还预测](01_Titanic_Prediction/)

891 条样本，完整走一遍 EDA → 缺失值处理 → 特征工程 → 建模 → 评估。决策树 / 随机森林 / KNN 对比，最佳 **83.15%**（5 折交叉验证 **82.01%**）。

两个反直觉的结论：

- 从姓名里拆出称呼（Mr / Mrs / Miss / Master），准确率从 81.46% 提到 **83.15%**；
- 300 棵树的随机森林（交叉验证 79.98%）**输给了一棵 depth=3 的单棵树**——小数据上，简单模型更抗过拟合。

`Python` · `Pandas` · `scikit-learn`

### 4. [加州房价预测](02_House_Price/)

随机森林回归预测街区房价中位数，用 MAE / RMSE 评估，`joblib` 保存模型后做单条样本推理。

`Python` · `scikit-learn` · `joblib`

## 📂 仓库结构

```text
AI-Portfolio/
├── 01_Titanic_Prediction/   notebook + 数据 + 说明
├── 02_House_Price/          训练脚本
├── 03_Spam_API/             FastAPI 服务
└── 04_LLM_Agent/            Text-to-SQL Agent + 50 题评测
```

每个目录下都有独立的 README，写清楚了这个项目解决什么问题、怎么跑、结果如何、踩过什么坑。

## 📫 联系我

- GitHub：[@xiongyu7](https://github.com/xiongyu7)
- 邮箱：2493552934@qq.com
- 求职方向：AI 应用开发 / 数据分析 · 2027 届

---

*保持热爱，持续学习中。*
