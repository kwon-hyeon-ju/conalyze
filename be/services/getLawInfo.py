import requests
import os
from dotenv import load_dotenv

load_dotenv()
email_id = os.getenv('LAW_API_KEY')

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

