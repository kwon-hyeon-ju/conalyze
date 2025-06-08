from flask import Flask
from routers.upload import upload_bp
from routers.ocr_router import ocr_bp

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False  # 한글 깨짐 방지

# 블루프린트 등록
app.register_blueprint(upload_bp, url_prefix="/upload")
app.register_blueprint(ocr_bp, url_prefix="/ocr")

@app.route("/")
def index():
    return "근로 계약서에서 불법적인 내용이나 포함되지 않은 내용들을 찾아주는 서비스"
