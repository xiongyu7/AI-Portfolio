"""垃圾邮件识别 API —— 文本分类 + HTTP 服务封装的最小完整示例。

训练数据只有 6 条样例，所以它是个"能跑通全流程"的教学项目，不是可用的过滤器。
真要用，把 TRAIN_TEXTS 换成 SMS Spam Collection 之类的公开数据集（5000+ 条）。

启动服务：
    uvicorn main:app --reload

调用接口：
    curl -X POST http://127.0.0.1:8000/predict \
         -H "Content-Type: application/json" \
         -d '{"text": "Free money! Click here to claim your prize."}'
"""

from fastapi import FastAPI
from pydantic import BaseModel
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB

# ---------------------------------------------------------------- 训练数据
TRAIN_TEXTS = [
    "Win a free iPhone now, click the link!",
    "Hey, are we still meeting for lunch today?",
    "Congratulations! You've won a $1000 gift card. Claim now!",
    "Please find attached the report for last quarter.",
    "URGENT: Your account has been suspended. Click here to verify.",
    "Can you send me the notes from yesterday's class?",
]
TRAIN_LABELS = ["spam", "ham", "spam", "ham", "spam", "ham"]

# 训练发生在模块加载时：数据量这么小，启动即训练比维护模型文件更省事。
vectorizer = CountVectorizer()
model = MultinomialNB()
model.fit(vectorizer.fit_transform(TRAIN_TEXTS), TRAIN_LABELS)

# ---------------------------------------------------------------- 接口
app = FastAPI(title="垃圾邮件识别 API", version="1.0.0")


class EmailRequest(BaseModel):
    text: str


class PredictionResponse(BaseModel):
    text: str
    label: str
    is_spam: bool


@app.get("/")
def health() -> dict:
    return {"status": "ok", "service": "spam-classifier", "endpoints": ["/predict"]}


@app.post("/predict", response_model=PredictionResponse)
def predict(request: EmailRequest) -> PredictionResponse:
    vector = vectorizer.transform([request.text])
    label = str(model.predict(vector)[0])
    return PredictionResponse(text=request.text, label=label, is_spam=label == "spam")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
