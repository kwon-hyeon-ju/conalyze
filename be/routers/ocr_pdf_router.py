from flask import Blueprint, request, jsonify
from pathlib import Path
import os
import uuid
import traceback
from pdf2image import convert_from_path
from services.ocr_service import naver_ocr
from dotenv import load_dotenv
from services.getAdvice import get_openai_response

load_dotenv()
ocr_file_bp = Blueprint("ocr_file", __name__)

BASE_DIR = Path(__file__).resolve().parents[1]
UPLOAD_DIR = BASE_DIR / "uploads"
POPPLER_PATH = r"C:\Users\ghdyx\Downloads\Release-24.08.0-0\poppler-24.08.0\Library\bin"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@ocr_file_bp.route("/ocr/file", methods=["POST"])
def ocr_file():
    try:
        if 'file' not in request.files:
            return jsonify(success=False, error="No file provided"), 400

        file = request.files['file']
        file_uuid = str(uuid.uuid4())
        file_ext = os.path.splitext(file.filename)[-1].lower()
        save_path = UPLOAD_DIR / f"{file_uuid}{file_ext}"
        file.save(save_path)

        total_text = ""
        all_raw = []

        if file_ext == ".pdf":
            images = convert_from_path(str(save_path), poppler_path=POPPLER_PATH)
            for i, image in enumerate(images):
                image_path = UPLOAD_DIR / f"{file_uuid}_page_{i+1}.png"
                image.save(image_path, format="PNG")
                ocr_result = naver_ocr(str(image_path))

                if "text" not in ocr_result or "raw" not in ocr_result:
                    return jsonify(success=False, error="'text' or 'raw' key missing", ocr_result=ocr_result)

                total_text += ocr_result["text"] + "\n"
                all_raw.append(ocr_result["raw"])

        elif file_ext in [".png", ".jpg", ".jpeg"]:
            ocr_result = naver_ocr(str(save_path))
            if "text" not in ocr_result or "ocr_result" not in ocr_result:
                return jsonify(success=False, error="'text' or 'raw' key missing", ocr_result=ocr_result)

            total_text = ocr_result["text"]
            all_raw.append(ocr_result["ocr_result"])

        else:
            return jsonify(success=False, error=f"지원되지 않는 파일 형식입니다: {file_ext}")

        # 텍스트 저장
        text_file_path = UPLOAD_DIR / f"{file_uuid}_ocr.txt"
        with open(text_file_path, "w", encoding="utf-8") as txt_file:
            txt_file.write(total_text.strip())

        # AI 분석
        ai_result = get_openai_response(total_text.strip(), "fineTuningFiles")
        if not ai_result or "법령분석" not in ai_result:
            return jsonify(success=False, error="GPT 분석 실패", ai_result=ai_result)

        return jsonify(
            success=True,
            uuid=file_uuid,
            text=total_text.strip(),
            raw=all_raw,
            ai_result=ai_result
        )

    except Exception as e:
        return jsonify(
            success=False,
            error=str(e),
            type=type(e).__name__,
            trace=traceback.format_exc()
        )
