# 02 · 加州房价预测

回归项目：用 8 个特征（收入中位数、房龄、房间数、地理位置等）预测街区房价中位数。

## 文件

| 文件 | 说明 |
| --- | --- |
| `house_predictor.py` | 训练 + 评估 + 保存模型 + 单条推理 |

> `house.ipynb` 待补充（特征重要性、误差分布分析）。当前脚本已能完整跑通流程。

## 运行

```bash
pip install scikit-learn pandas joblib
python house_predictor.py
```

数据是 `sklearn.datasets.fetch_california_housing()` 自带的 2 万条样本，首次运行会自动下载，不需要手动准备 CSV。

## 输出

脚本会打印 MAE / RMSE，并把模型保存为 `california_house_model.pkl`，最后从测试集抽一条样本做推理演示。

## 说明

- 目标变量原始单位是 10 万美元，脚本里乘 `100000` 还原成美元展示；
- 随机森林在这里属于"够用"的选择：树模型能自动处理特征之间的非线性关系，不需要额外做标准化。
