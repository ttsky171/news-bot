import streamlit as st
import json
import http.client
import os
import datetime

# 페이지 설정
st.set_page_config(page_title="실시간 뉴스 블로그 생성기", page_icon="📰", layout="wide")

# 폴더 관리
HISTORY_DIR = "blog_history"
if not os.path.exists(HISTORY_DIR): os.makedirs(HISTORY_DIR)

def save_to_history(keyword, platform, content):
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_keyword = "".join(c for c in keyword if c.isalnum() or c in (' ', '_', '-')).strip()
    filename = f"{HISTORY_DIR}/{now}_{safe_keyword}_{platform}.txt"
    with open(filename, "w", encoding="utf-8") as f: f.write(content)

# 1. JSONBin 데이터 로드 (형이 준 코드 유지)
def load_extension_data():
    import urllib.request
    BIN_ID = "6a0c24886610dd3ae86c19cd"
    MASTER_KEY = "$2a$10$XJlSzhQ1AoOvMQqIH95KOeLDbr7ohp4ocKXh2V3iAJxHW.QvAnOm6"
    try:
        url = f"https://api.jsonbin.io/v3/b/{BIN_ID}"
        req = urllib.request.Request(url, headers={"X-Master-Key": MASTER_KEY})
        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            actual = res_data.get("record", {})
            return actual.get("keywords", []), actual.get("metadata", {}), actual.get("updated_at", "미정")
    except:
        return [], {}, "연동 대기 중"

# 2. AI 호출 엔진 (프롬프트 제어 포함)
def call_ai_prime_tech(key, sys_prompt, user_msg, model_name):
    host = "aiprimetech.io"
    payload = json.dumps({
        "model": model_name,
        "max_tokens": 4000, 
        "messages": [{"role": "user", "content": f"[System 규칙: {sys_prompt}]\n\n{user_msg}"}]
    })
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {key}'}
    
    conn = http.client.HTTPSConnection(host, timeout=60)
    conn.request("POST", "/v1/messages", payload, headers)
    res = conn.getresponse()
    data = res.read().decode("utf-8")
    conn.close()
    
    result_json = json.loads(data)
    # Claude 응답 구조에 맞게 텍스트 추출
    return result_json.get("content", [{}])[0].get("text", "생성 실패")

# 3. 화면 UI
st.title("📰 실시간 이슈 뉴스 블로그 글 생성기")

# 사이드바
st.sidebar.header("🔑 설정 및 시그널")
api_key = st.sidebar.text_input("AI Prime Tech API Key", type="password")
model = st.sidebar.selectbox("모델 선택", ["claude-sonnet-4-6", "claude-opus-4-6"])

live_kws, live_metadata, last_update = load_extension_data()
query = st.sidebar.selectbox("작성할 키워드 선택", live_kws if live_kws else ["대기 중..."])
platforms = st.sidebar.multiselect("발행 플랫폼", ["네이버 블로그", "티스토리"], default=["네이버 블로그"])
style = st.sidebar.selectbox("글 스타일", ["📰 뉴스 보도체", "😊 쉬운 설명체"])

# 메인 생성 로직
if st.sidebar.button("✨ 글 생성하기", type="primary"):
    if not api_key:
        st.error("API 키를 입력하세요.")
    else:
        factual_summary = live_metadata.get(query, "최신 정보 없음")
        
        for p in platforms:
            sys_prompt = f"당신은 파워블로거입니다. 제공된 요약 정보를 바탕으로 글을 쓰세요. 본문 내 '**' 기호는 절대 금지합니다."
            user_msg = f"키워드: {query}\n요약: {factual_summary}\n\n이 내용을 바탕으로 블로그 글을 작성해줘."
            
            with st.spinner(f"{p} 생성 중..."):
                content = call_ai_prime_tech(api_key, sys_prompt, user_msg, model)
                st.subheader(f"{p} 결과물")
                st.text_area("내용", value=content, height=500)
                save_to_history(query, p, content)
