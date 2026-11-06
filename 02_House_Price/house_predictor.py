"""加州房价预测 —— 训练、评估、保存模型、模拟推理。

数据用的是 sklearn 自带的 California Housing（2 万条，8 个特征），
不需要自己下载，第一次运行会自动获取。

运行：
    python house_predictor.py

产物：
    california_house_model.pkl   训练好的随机森林
"""

import joblib
from sklearn.datasets import fetch_california_housing
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, root_mean_squared_error
from sklearn.model_selection import train_test_split

# 目标变量以 10 万美元为单位，展示时乘以 100000 换成美元
UNIT = 100_000


def main() -> None:
    print("正在加载加州房价数据...")
    housing = fetch_california_housing()
    X, y = housing.data, housing.target
    print(f"样本数 {X.shape[0]}，特征数 {X.shape[1]}：{housing.feature_names}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    print("正在训练随机森林...")
    model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    mae = mean_absolute_error(y_test, predictions)
    rmse = root_mean_squared_error(y_test, predictions)
    print(f"平均绝对误差（MAE）：{mae * UNIT:,.0f} 美元")
    print(f"均方根误差（RMSE）：{rmse * UNIT:,.0f} 美元")

    joblib.dump(model, "california_house_model.pkl")
    print("模型已保存为 california_house_model.pkl")

    # 从测试集里抽一条做推理演示
    sample = X_test[0].reshape(1, -1)
    predicted, actual = model.predict(sample)[0], y_test[0]
    print("\n--- 单条样本预测 ---")
    print(f"真实房价：{actual * UNIT:,.0f} 美元")
    print(f"模型预测：{predicted * UNIT:,.0f} 美元")
    print(f"绝对误差：{abs(actual - predicted) * UNIT:,.0f} 美元")


if __name__ == "__main__":
    main()
