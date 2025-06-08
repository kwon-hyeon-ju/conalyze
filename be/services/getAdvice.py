import openai
import os
import csv
import json
import re
from dotenv import load_dotenv
import requests

load_dotenv()
email_id = os.getenv('LAW_API_KEY')
# .env 파일에서 API 키 불러오기
openai.api_key = os.getenv('OPENAI_KEY')

def extract_laws_from_json(json_data):
    law_list = []
    for item in json_data.get("관련법조항", []):
        law_name = item.get("법령명")
        article = item.get("조항") or item.get("조 항")  # 띄어쓰기 오류 대응
        if law_name and article:
            law_list.append({
                "법령명": law_name.strip(),
                "조항": article.strip().replace("조", "")
            })
    return law_list

def get_law_id(law_name, email_id):
    search_url = "http://www.law.go.kr/DRF/lawSearch.do"
    search_params = {
        "OC": email_id,
        "target": "law",
        "type": "JSON",
        "query": law_name,
        "mobileYn": "Y",
        "display": 1,
        "page": 1,
    }
    search_response = requests.get(search_url, params=search_params)
    if search_response.status_code == 200:
        try:
            search_data = search_response.json()
            law = search_data['LawSearch']['law']
            if isinstance(law, list):  # 결과가 여러 개인 경우
                return law[0]['법령ID']
            return law['법령ID']
        except Exception as e:
            return f"Error parsing law ID JSON: {str(e)}"
    return f"Error retrieving law ID: {search_response.status_code}"

def get_law_article(law_id, article_number, email_id):
    law_article_url = "http://www.law.go.kr/DRF/lawService.do"
    try:
        article_number_formatted = f"00{int(article_number):02d}00"
    except:
        return f"Invalid article number: {article_number}"
    law_article_params = {
        "OC": email_id,
        "target": "law",
        "type": "JSON",
        "ID": law_id,
        "JO": article_number_formatted,
        "mobileYn": "Y",
    }
    article_response = requests.get(law_article_url, params=law_article_params)
    if article_response.status_code == 200:
        try:
            return article_response.json()
        except Exception as e:
            return f"Error parsing article JSON: {str(e)}"
    return f"Error retrieving law article: {article_response.status_code}"

def get_all_law_details_as_json(json_data):
    law_refs = extract_laws_from_json(json_data)
    results = []

    for ref in law_refs:
        law_name = ref["법령명"]
        article_number = ref["조항"]

        # 법령ID 조회
        law_id = get_law_id(law_name, email_id)
        if not isinstance(law_id, str) or not law_id.isdigit():
            results.append(f"""
                {{
                    "법령명": "{law_name}",
                    "조항 번호": "{article_number}",
                    "조문 내용": "법령ID 조회 실패: {law_id}"
                }}
            """)
            continue

        # 법령 조문 조회
        article_content = get_law_article(law_id, article_number, email_id)
        if not isinstance(article_content, str):  # 수정: dict에서 str로 변경
            results.append(f"""
                {{
                    "법령명": "{law_name}",
                    "조항 번호": "{article_number}",
                    "조문 내용": "법령 조문 조회 실패: {article_content}"
                }}
            """)
            continue

        try:
            clause_texts = []
            # 기사 내용 (여기서는 str로 처리)
            articles = article_content  # 이미 str로 받았다고 가정

            # 조문 파싱 처리
            if articles:
                clause_texts.append(articles.strip())  # 조문 내용이 있다면 이를 추가
            else:
                clause_texts.append("조문 내용 없음")

            results.append(f"""
                {{
                    "법령명": "{law_name}",
                    "조항 번호": "{article_number}",
                    "조문 내용": "{'\\n'.join(clause_texts)}"
                }}
            """)
        except Exception as e:
            results.append(f"""
                {{
                    "법령명": "{law_name}",
                    "조항 번호": "{article_number}",
                    "조문 내용": "조문 파싱 실패: {str(e)}"
                }}
            """)

    # 결과는 JSON 문자열의 목록으로 반환
    return results


### --- CSV 관련 함수들 --- ###

def load_csv_data_by_name(filename, folder_path):
    file_path = os.path.join(folder_path, filename)
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            return list(csv.DictReader(f))
    except UnicodeDecodeError:
        with open(file_path, 'r', encoding='cp949') as f:
            return list(csv.DictReader(f))

def extract_law_info_from_text(text):
    # 예: "근로기준법 제50조", "가사근로자법 제28조"
    match = re.match(r"(.+?)\s*제\s*(\d+[조항]*)", text)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return None, None

def match_laws_with_csv(gpt_law_list, law_content_csv, law_meta_csv):
    matched_laws = []

    for entry in gpt_law_list:
        law_name, article = extract_law_info_from_text(entry)
        if not law_name or not article:
            continue

        # 1. 조문 내용 찾기
        matched_content = next(
            (row for row in law_content_csv
             if law_name.replace(" ", "") in row.get("법령명", "").replace(" ", "")
             and article in row.get("조문명", "")),
            None
        )

        # 2. 메타 정보 찾기
        matched_meta = next(
            (row for row in law_meta_csv
             if law_name.replace(" ", "") in row.get("법령명", "").replace(" ", "")),
            None
        )

        matched_laws.append({
            "법령명": matched_meta.get("법령명") if matched_meta else law_name,
            "조항": article,
            "공포번호": matched_meta.get("공포번호", "미확인") if matched_meta else "미확인",
            "시행일자": matched_meta.get("시행일자", "미확인") if matched_meta else "미확인",
            "법령내용": matched_content.get("조문명", "해당 조문을 찾을 수 없습니다.") if matched_content else "해당 조문을 찾을 수 없습니다."
        })

    return matched_laws

### --- GPT 계약서 분석 --- ###

def analyze_contract(contract_text):
    prompt = f"""
    이 계약서 내용을 아래 항목에 따라 분석해 주세요:

    1. **계약서 필수 기재사항 누락 여부 확인**
    2. **대한민국 근로기준법 및 관련 법령과의 관련성 및 위반 여부 판단**
    3. **위반이 있다면 구체적인 위반 내용과 해당 법령 조항 명시**
    4. **계약서 내용과 관련 있는 모든 법령 조항 명시 (위반 여부와 상관 없이)** 
    5. **임금 구조의 적절성 판단**
    6. **사회보험 적용 여부의 적절성**
    7. **기타 유의사항 및 계약서에서 잘못 해석될 수 있는 부분 설명**
    8. **근로자에게 불리하게 작용할 수 있는 조항이 있는 경우 설명**
    9. **총평 및 권고사항**

    출력 형식은 아래 JSON만 사용하세요. 다른 텍스트는 포함하지 마세요.

    ```json
    {{
      "필수사항누락": ["항목1", "항목2", ...],
      "위반여부": "예" 또는 "아니오",
      "위반세부사항": ["설명1", "설명2", ...],
      "관련법조항": ["근로기준법 제00조", "최저임금법 제0조", ...],
      "법령내용": ["조항 내용1", "조항 내용2", ...],
      "임금구조평가": "간단 요약 또는 문제점",
      "사회보험평가": "간단 요약 또는 문제점",
      "기타유의사항": ["설명1", "설명2", ...],
      "총평": "전반적인 평가와 권고사항"
    }}
    """
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "당신은 대한민국 노동법 전문가입니다."},
            {"role": "user", "content": "아래는 한 근로계약서입니다. 내용을 분석해 주세요."},
            {"role": "user", "content": contract_text},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1500,
        temperature=0
    )

    try:
        result_text = response['choices'][0]['message']['content'].strip()

        if result_text.startswith("```json"):
            result_text = re.sub(r"```json\s*|\s*```", "", result_text, flags=re.DOTALL).strip()

        return result_text  # JSON으로 변환하지 않고 문자열 그대로 반환

    except Exception as e:
        return {"error": str(e), "raw_output": result_text}

### --- 1차 계약서 분석: csv 파일 참고해서 결과 출력 --- ###

def get_analysis_with_law_matching(contract_text, csv_folder_path):
    # 2. GPT 분석 실행 (문자열 반환 가정)
    gpt_result_str = analyze_contract(contract_text)

    try:
        # 문자열을 JSON 딕셔너리로 파싱
        gpt_result = json.loads(gpt_result_str)
    except json.JSONDecodeError as e:
        return {"error": "GPT 결과를 JSON으로 파싱할 수 없습니다.", "detail": str(e), "raw_output": gpt_result_str}

    # 3. GPT가 추정한 법령조항 리스트
    gpt_laws = gpt_result.get("관련법조항", [])

    # 4. CSV 각각 로드
    law_content_csv = load_csv_data_by_name("고용노동부_고용노동관련 법령 내용_20250227.csv", csv_folder_path)
    law_meta_csv = load_csv_data_by_name("고용노동부_고용노동관련 법령_20250227.csv", csv_folder_path)

    # 5. GPT 결과를 CSV 기준으로 보정
    matched_laws = match_laws_with_csv(gpt_laws, law_content_csv, law_meta_csv)

    # 6. 결과 JSON에 반영
    gpt_result["관련법조항"] = matched_laws

    return gpt_result

def get_final_contract_analysis(result, result2):
    """
    계약서 분석 결과(result)와 관련 법령 상세 내용(result2)을 바탕으로
    GPT에게 보강된 분석을 요청하는 함수

    Args:
        result (dict): GPT의 1차 분석 결과 (JSON 디코딩된 딕셔너리)
        result2 (str): 관련 법령 상세 내용 (JSON 형식의 문자열)

    Returns:
        dict: 보강된 분석 결과 JSON 또는 오류 메시지
    """
    prompt = f"""
    다음은 GPT가 근로계약서를 1차 분석한 결과(result)와 관련 법령의 상세 조문 내용(result2)입니다. 이 두 데이터를 바탕으로 계약서에 대한 보다 정밀한 분석을 다시 수행해 주세요.

    법령 조항별로 다음 항목을 묶어서 제시해 주세요:
    - "법령명"
    - "관련법조항"
    - "공포번호"
    - "시행일자"
    - "조문내용": "근로기준법 제17조: ... 와 같은 형식으로 요약"
    - "위반여부": "예" 또는 "아니오"
    - "위반사항및법적해석": 위반된 경우 위반 사유와 해석
    - "상세분석": 법령과 계약서의 연결 및 위반 판단에 대한 상세 설명

    그 다음으로는 다음 항목들을 계약서 전체 기준으로 종합하여 작성해 주세요:
    - "필수사항누락": ["항목1", "항목2", ...]
    - "임금구조평가": "간단 요약 또는 문제점"
    - "사회보험평가": "간단 요약 또는 문제점"
    - "기타유의사항": ["설명1", "설명2", ...]
    - "총평": "전반적인 평가와 권고사항"

    출력 형식은 아래 JSON만 사용하세요. 다른 텍스트는 포함하지 마세요.
    다음은 원래 분석 결과(result)입니다: {result}
    다음은 각 관련 조항의 상세 내용(result2)입니다: {result2}

    ```json
    {{
        "법령분석": [
        {{
        "법령명": "근로기준법",
        "조항": "17조",
        "공포번호": "제20520호",
        "시행일자": "2025-02-23",
        "조문내용": "근로기준법 제17조: 근로계약서에 임금, 소정근로시간, 휴일, 연차유급휴가 등을 명시해야 함.",
        "위반여부": "예",
        "위반사항및법적해석": "근로기준법 제17조 위반: 주휴수당 금액 및 기타급여(제수당 등)가 명시되지 않음.",
        "상세분석": "근로기준법 제17조에 따라 근로계약서에는 임금의 구성항목, 계산방법, 지급방법 등이 명시되어야 하나, 주휴수당 및 기타급여가 명시되지 않아 위반됨."
        }},
        ...
        ],
        "필수사항누락": ["항목1", "항목2", ...],
        "임금구조평가": "요약 내용",
        "사회보험평가": "요약 내용",
        "기타유의사항": ["내용1", "내용2", ...],
        "총평": "전반적 평가 및 권고사항"
        }}

        반드시 JSON 형식으로만 출력해 주세요. 다른 텍스트는 포함하지 마세요.
        """
    
    try:
        response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
        {"role": "system", "content": "당신은 대한민국 노동법에 정통한 계약서 분석 전문가입니다."},
        {"role": "user", "content": prompt}
    ],
    temperature=0,
    max_tokens=5000
    )
        result_text = response["choices"][0]["message"]["content"]

        # JSON 부분만 추출
        if result_text.startswith("```json"):
            result_text = re.sub(r"```json\s*|\s*```", "", result_text, flags=re.DOTALL).strip()

            return result_text

    except json.JSONDecodeError:
        return {"error": "GPT 응답이 JSON 형식이 아닙니다.", "raw_output": result_text}
    except Exception as e:
        return {"error": str(e)}
    
### --- 최종 계약서 분석: 총평을 JSON 형식으로 정리 --- ###
def final_check(summary_text):
    """
    총평 텍스트를 받아 GPT에게 JSON 형식으로만 재정리된 출력을 요청하는 함수

    Args:
        summary_text (str): "총평" 항목의 분석 요약 텍스트

    Returns:
        dict or str: JSON 문자열 형식의 응답 또는 오류 메시지
    """
    prompt = f"""
    다음은 계약서 분석의 종합 평가 내용입니다. 이를 보기 좋게 정리된 JSON 형식으로 다시 출력해 주세요.
    
    반드시 다음 조건을 지켜주세요:
    - JSON 형식 외의 텍스트는 절대 포함하지 마세요.
    - 출력에는 서두, 설명, 주석 없이 JSON만 포함하세요.

    입력된 총평 내용:
    "{summary_text}"

    출력 형식 예시는 다음과 같아야 합니다:
    ```json
    {{
        총평: "계약서의 기본적인 틀은 갖추고 있으나, 주휴수당 및 기타급여 항목의 구체적 명시가 필요하며, 상여금 지급 여부를 명확히 해야 합니다. 또한, 오타를 수정하여 명확한 계약서를 작성하는 것이 필요합니다.",
        위반여부: "예",
        {{
        "법령명": "근로기준법",
        "조항": "17조",
        "공포번호": "제20520호",
        "시행일자": "2025-02-23",
        "조문내용": "근로기준법 제17조: 근로계약서에 임금, 소정근로시간, 휴일, 연차유급휴가 등을 명시해야 함.",
        "위반여부": "예",
        "위반사항및법적해석": "근로기준법 제17조 위반: 주휴수당 금액 및 기타급여(제수당 등)가 명시되지 않음.",
        "상세분석": "근로기준법 제17조에 따라 근로계약서에는 임금의 구성항목, 계산방법, 지급방법 등이 명시되어야 하나, 주휴수당 및 기타급여가 명시되지 않아 위반됨."
        }},
        ...
        ],
        "필수사항누락": ["항목1", "항목2", ...],
        "임금구조평가": "요약 내용",
        "사회보험평가": "요약 내용",
        "기타유의사항": ["내용1", "내용2", ...],
        "총평": "전반적 평가 및 권고사항"
    }}

    ```
    위 예시처럼 출력 결과는 반드시 JSON 블록으로만 구성해 주세요.
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "당신은 계약서 분석 결과를 형식화하는 전문가입니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=5000
        )
        result_text = response["choices"][0]["message"]["content"]

        # JSON 블록만 추출
        if result_text.startswith("```json"):
            result_text = re.sub(r"```json\s*|\s*```", "", result_text, flags=re.DOTALL).strip()

        return result_text

    except Exception as e:
        return {"error": str(e)}


### --- 2차 계약서 분석: CSV 파일 참고된 결과 + 법령api를 사용해서 얻은 결과 --- ###

def get_openai_response(contract_text, csv_folder_path):
    # 1차 계약서 분석: CSV 파일 참고된 결과
    result = get_analysis_with_law_matching(contract_text, csv_folder_path)

    # 2차 계약서 분석: 법령 API를 사용해서 얻은 결과
    result2 = get_all_law_details_as_json(result)
    
    # 최종 결과
    final_result = get_final_contract_analysis(result, result2)
    final_final_result = final_check(final_result)

    try:
        # 문자열을 JSON 객체로 변환
        return json.loads(final_final_result)
    except json.JSONDecodeError as e:
        return {"error": "최종 결과가 유효한 JSON 형식이 아닙니다.", "detail": str(e), "raw": final_final_result}

