# 03 · 垃圾邮件识别 API

把一个文本分类模型封装成 HTTP 服务，是"模型 → 产品"之间最短的一段路。

## 文件

| 文件 | 说明 |
| --- | --- |
| `main.py` | FastAPI 服务，含训练数据、模型和接口 |

## 运行

```bash
pip install fastapi uvicorn scikit-learn
uvicorn main:app --reload
```

打开 <http://127.0.0.1:8000/docs> 可以直接在浏览器里调接口（FastAPI 自动生成的 Swagger 文档）。

## 调用

```bash
curl -X POST http://127.0.0.1:8000/predict \
     -H "Content-Type: application/json" \
     -d "{\"text\": \"Free money! Click here to claim your prize.\"}"
```

返回：

```json
{
  "text": "Free money! Click here to claim your prize.",
  "label": "spam",
  "is_spam": true
}
```

## 说明

- 模型是 `CountVectorizer` + `MultinomialNB`，文本分类的经典组合，训练只需要毫秒级；
- 训练数据只有 6 条样例，**这是个教学项目，不是能用的过滤器**。要真用，把 `TRAIN_TEXTS` 换成 SMS Spam Collection 之类的公开数据集；
- 训练放在模块加载时执行，所以启动即就绪，不需要额外维护模型文件。真实项目里应该改成 `joblib` 加载离线训练好的模型。
