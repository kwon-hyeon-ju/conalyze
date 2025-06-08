from services.getAdvice import get_analysis_with_law_matching, get_openai_response
from services.getLawInfo import get_all_law_details_as_json

import os
import json
from dotenv import load_dotenv
load_dotenv()

# 상대 경로
contract_file_path = os.path.join("be", "uploads", "img.png_ocr.txt")
csv_folder_path = os.path.join("be", "fineTuningFiles")

# 1차 분석
gpt_result = get_analysis_with_law_matching(contract_file_path, csv_folder_path)

# 2차 법령 API 분석
law_result = get_all_law_details_as_json(gpt_result)

# 결과 출력
print("GPT 분석 결과:")
print(json.dumps(gpt_result, indent=2, ensure_ascii=False))

print("\n법령 상세 조회 결과:")
print(json.dumps(law_result, indent=2, ensure_ascii=False))