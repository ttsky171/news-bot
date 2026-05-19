import streamlit as st
import json
import http.client
from urllib.parse import urlparse
import datetime
import os
import urllib.request # 추가됨

# 웹사이트 기본 레이아웃 테마 설정
st.set_page_config(page_title="실시간 뉴스 블로그 생성기", page_icon="📰", layout="wide")

st.markdown("""
    <style>
    .main {background-color: #0e1117; color: #fafafa;}
    div[data-baseweb="select"] {background-color: #1a1c23;}
    </style>
    """, unsafe_allow_html=True)

# 원고 저장을 위한 로컬 폴더 생성 및 관리
HISTORY_DIR = "blog_history"

if not os.path.exists(HISTORY_DIR):
    os.makedirs(HISTORY_DIR)

def save_to_history(keyword, platform, content):
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_keyword = "".join(c for c in keyword if c.isalnum() or c in (' ', '_', '-')).strip()
    filename = f"{HISTORY_DIR}/{now}_{safe_keyword}_{platform}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

def get_history_files():
    files = [f for f in os.listdir(HISTORY_DIR) if f.endswith(".txt")]
    files.sort(reverse=True)
    return files

# -------------------------------------------------------------
# [🛠️ 수신 엔진] 우체통에서 데이터를 직접 뽑아오는 최신 엔진
# -------------------------------------------------------------
def load_extension_data():
    """인터넷 우체통(JSONBin)에서 확장 프로그램이 던진 데이터를 실시간으로 가져옴"""
    BIN_ID = "6a0c24886610dd3ae86c19cd"
    MASTER_KEY = "$2a$10$XJlSzhQ1AoOvMQqIH95KOeLDbr7ohp4ocKXh2V3iAJxHW.QvAnOm6"
    url = f"https://api.jsonbin.io/v3/b/{BIN_ID}/latest"
    
    try:
        req = urllib.request.Request(url, headers={"X-Master-Key": MASTER_KEY})
        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            # 디버깅용: 데이터를 그대로 화면에 찍어보자 (나중에 지워도 됨)
            print("우체통에서 읽은 데이터:", res_data) 
            
            # record가 있으면 꺼내고, 없으면 전체 데이터를 사용
            actual_data = res_data.get("record", res_data)
            
            return (
                actual_data.get("keywords", ["데이터가", "없음"]), 
                actual_data.get("metadata", {}), 
                actual_data.get("updated_at", "동기화 실패")
            )
    except Exception as e:
        return ["에러발생", str(e)], {}, "연결 오류"

# API Key 저장/불러오기
if "api_key_saved" not in st.session_state:
    st.session_state["api_key_saved"] = ""

st.markdown(
    """
    <script>
    const savedKey = localStorage.getItem("prime_tech_api_key");
    if (savedKey) {
        parent.window.postMessage({type: "streamlit:setComponentValue", value: savedKey}, "*");
    }
    </script>
    """,
    unsafe_allow_html=True
)

st.title("📰 실시간 이슈 뉴스 블로그 글 생성기")
st.caption("AI 프라임텍 전용 클라우드 노드 구동 엔진 · 크롬 확장 프로그램 실시간 API 동계 연동")

st.sidebar.header("🔑 인증 및 옵션 설정")
api_key = st.sidebar.text_input("AI Prime Tech API Key 입력", value=st.session_state["api_key_saved"], type="password")

if api_key and api_key != st.session_state["api_key_saved"]:
    st.session_state["api_key_saved"] = api_key
    st.markdown(f"<script>localStorage.setItem('prime_tech_api_key', '{api_key}');</script>", unsafe_allow_html=True)

selected_model = st.sidebar.selectbox("🤖 Claude 모델 선택", ["claude-sonnet-4-6", "claude-opus-4-6", "claude-opus-4-7"], index=0)

st.sidebar.markdown("---")
st.sidebar.subheader("📡 크롬 확장 프로그램 동기화 상태")

# 실시간 데이터 로드
live_kws, live_metadata, last_update = load_extension_data()

if live_kws:
    st.sidebar.success(f"✅ 연동 완료! (최근 동기화: {last_update})")
    options_list = live_kws
else:
    st.sidebar.warning("⚠️ 시그널 창을 크롬 탭에 띄워두세요.")
    options_list = ["크롬 확장 프로그램의 신호를 기다리는 중..."]

query = st.sidebar.selectbox("🎯 작성할 최적화 키워드 선택", options_list)
platforms = st.sidebar.multiselect("🖥 발행 플랫폼 선택", ["워드프레스", "네이버 블로그", "티스토리"], default=["네이버 블로그"])
style = st.sidebar.selectbox("✍️ 글 스타일", ["📰 뉴스 보도체", "😊 쉬운 Explanation체", "💬 분석/의견체", "⚡ 짧은 요약체"])
length = st.sidebar.selectbox("📏 글 길이", ["짧게 (500자)", "보통 (1000자)", "길게 (2000자)"])

def call_ai_prime_tech(key, sys_prompt, user_msg, model_name):
    host = "aiprimetech.io"
    payload = json.dumps({
        "model": model_name,
        "max_tokens": 4000, 
        "messages": [{"role": "user", "content": f"[System 규칙: {sys_prompt}]\n\n요청 과제: {user_msg}"}]
    })
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {key}'}
    conn = http.client.HTTPSConnection(host, timeout=60)
    conn.request("POST", "/v1/messages", payload, headers)
    res = conn.getresponse()
    data = res.read().decode("utf-8")
    conn.close()
    return data

if st.sidebar.button("✨ 플랫폼별 블로그 글 생성", type="primary"):
    if not api_key:
        st.error("API 키를 입력해주세요.")
    else:
        factual_summary = live_metadata.get(query, "실시간 핵심 이슈 트렌드")
        for p in platforms:
            with st.spinner(f"'{p}' 노출 원고 집필 중..."):
                res_content = call_ai_prime_tech(api_key, "뉴스 전문가", f"{query} - {factual_summary}", selected_model)
                st.text_area(f"{p} 결과물", value=res_content, height=300)
                save_to_history(query, p, res_content)

st.sidebar.markdown("---")
st.sidebar.header("🗂️ 과거 작성 원고")
for f in get_history_files():
    st.sidebar.text(f)
