import streamlit as st
import json
import http.client
from urllib.parse import urlparse
import datetime
import os
import re

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
st.caption("AI 프라임텍 전용 클라우드 노드 구동 엔진 · 시그널 텍스트 팩트 구조화 추출기")

# 사이드바 설정
st.sidebar.header("🔑 인증 및 옵션 설정")

if st.session_state["api_key_saved"]:
    default_key = st.session_state["api_key_saved"]
else:
    default_key = ""

api_key = st.sidebar.text_input("AI Prime Tech API Key 입력", value=default_key, type="password")

if api_key and api_key != st.session_state["api_key_saved"]:
    st.session_state["api_key_saved"] = api_key
    st.markdown(f"<script>localStorage.setItem('prime_tech_api_key', '{api_key}');</script>", unsafe_allow_html=True)

selected_model = st.sidebar.selectbox("🤖 Claude 모델 선택", ["claude-sonnet-4-6", "claude-opus-4-6", "claude-opus-4-7"], index=0)

# -------------------------------------------------------------
# [전면 수정] 복사 붙여넣기 데이터 기반 정밀 추출 섹션
# -------------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.subheader("📋 Signal.bz 화면 복사·붙여넣기")

# 사용자가 시그널 사이트 화면을 통째로 긁어다 붙이는 공간
raw_signal_data = st.sidebar.text_area(
    "시그널 사이트 전체 선택(Ctrl+A) 후 여기에 붙여넣기(Ctrl+V)", 
    height=180, 
    placeholder="예시:\n1위 키워드명\n뉴스 요약 내용...\n2위 키워드명\n뉴스 요약 내용..."
)

# 텍스트 데이터에서 키워드와 요약 내용을 지능적으로 매핑 분리하는 팩트 엔진
parsed_keywords = []
keyword_data_map = {}

if raw_signal_data:
    # 줄바꿈 단위로 쪼개기
    lines = [l.strip() for l in raw_signal_data.split("\n") if l.strip()]
    
    current_kw = None
    accumulated_summary = []
    
    for line in lines:
        # '1위 키워드' 또는 '1 키워드' 또는 그냥 키워드 패턴 인식
        match = re.match(r'^(\d+위?|\-\s+)?\s*(.+)$', line)
        if match:
            potential_kw = match.group(2).strip()
            
            # 단어가 너무 길지 않고 (키워드 특성), 메뉴명이 아니면 새로운 키워드로 인식
            if len(potential_kw) < 25 and potential_kw not in ["뉴스", "랭킹", "실시간 검색어", "로그인", "회원가입", "시그널", "Signal"]:
                # 이전 키워드의 요약문 저장
                if current_kw and accumulated_summary:
                    keyword_data_map[current_kw] = "\n".join(accumulated_summary)
                
                current_kw = potential_kw
                if current_kw not in parsed_keywords:
                    parsed_keywords.append(current_kw)
                accumulated_summary = []
            else:
                # 키워드가 아니라면 현재 키워드의 뉴스 요약 내용으로 축적
                if current_kw:
                    accumulated_summary.append(line)
                    
    # 마지막 키워드 잔여 데이터 저장
    if current_kw and accumulated_summary:
        keyword_data_map[current_kw] = "\n".join(accumulated_summary)

if parsed_keywords:
    query = st.sidebar.selectbox("🎯 작성할 최적화 키워드 선택", parsed_keywords)
else:
    query = st.sidebar.selectbox("🎯 작성할 최적화 키워드 선택", ["데이터를 먼저 붙여넣어 주세요"])

platforms = st.sidebar.multiselect("🖥 발행 플랫폼 선택 (복수 선택 가능)", ["워드프레스", "네이버 블로그", "티스토리"], default=["네이버 블로그"])
style = st.sidebar.selectbox("✍️ 글 스타일", ["📰 뉴스 보도체", "😊 쉬운 설명체", "💬 분석/의견체", "⚡ 짧은 요약체"])
length = st.sidebar.selectbox("📏 글 길이", ["짧게 (500자)", "보통 (1000자)", "길게 (2000자)"])

def call_ai_prime_tech(key, sys_prompt, user_msg, model_name):
    host = "aiprimetech.io"
    payload = json.dumps({
        "model": model_name,
        "max_tokens": 4000, 
        "messages": [{"role": "user", "content": f"[System 규칙: {sys_prompt}]\n\n요청 과제: {user_msg}"}]
    })
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {key}'}
    
    possible_paths = ["/v1/messages", "/v1/api/v1/messages", "/api/v1/messages"]
    data = b""
    res_status = 0
    
    for path in possible_paths:
        conn = http.client.HTTPSConnection(host, timeout=60)
        try:
            conn.request("POST", path, payload, headers)
            res = conn.getresponse()
            res_status = res.status
            data = res.read()
            if res_status == 200:
                break
        except:
            pass
        finally:
            conn.close()
            
    if res_status != 200:
        return f"❌ 대행 서버 통신 실패 (HTTP {res_status}): API 키 그룹이나 잔액을 재점검하세요."

    try:
        result_json = json.loads(data.decode("utf-8"))
        output_text = ""
        if "content" in result_json:
            c_list = result_json["content"]
            if isinstance(c_list, list):
                output_text = "".join([b.get("text", "") for b in c_list if isinstance(b, dict) and "text" in b])
            elif isinstance(c_list, dict):
                output_text = c_list.get("text", "")
        elif "choices" in result_json:
            choices = result_json["choices"]
            if choices and isinstance(choices, list):
                output_text = choices[0].get("message", {}).get("content", "")
        return output_text.strip()
    except Exception as e:
        return f"❌ 데이터 분석 오류: {str(e)}"

def get_system_prompt(p, style_desc, len_desc):
    shared = (
        f"당신은 대한민국 최고 수익을 올리는 네이버 파워블로거이자 SEO 마스터입니다. "
        f"함께 제공되는 시그널 사이트의 '실제 뉴스 요약문'을 철저한 팩트 뼈대로 삼으세요. 가상의 허구 사실을 절대 지어내지 말고 팩트를 정교하게 확장하여 인간형 문체로 작성하세요.\n\n"
        f"1. [이목 집중형 제목 강제 고정]: 원고의 첫 줄은 무조건 독자의 궁금증을 유발하고 클릭을 유도하는 자극적이고 트렌디한 제목으로 시작하세요. 중간에 특수기호(**)는 넣지 마세요.\n"
        f"2. [스마트블록 타겟 태그 폭탄]: 본문 맨 마지막에 네이버 스마트블록(인기글/주제별 검색)에 무조건 걸리도록 연관 키워드, 성별/연령별 타겟 키워드, 롱테일 키워드를 섞어 최소 20개 이상의 샵(#) 태그를 쏟아내세요.\n"
        f"3. [저작권 무죄 사진/링크 추천 섹션 생성]: 본문 하단에 블로거가 저작권 소송에 걸리지 않고 안전하게 쓸 수 있는 공식 사진 소스 가이드 5개를 정확하게 작성하세요. "
        f"정치/이슈/정부 관련 주제라면 대한민국 정부 공식 브리핑 사이트나 e-영상역사관 링크를 제공하고, 연예인/셀럽/스포츠 관련 주제라면 해당 인물의 오피셜 인스타그램 아이디나 공식 유튜브 채널 링크를 기반으로 어떤 장면을 캡처해야 하는지 5개의 구체적인 가이드를 생성하세요.\n"
        f"4. [기호 절대 금지]: 제목과 본문 한가운데에는 별표(**)나 화살표(▶) 같은 AI 서식 기호를 절대로 쓰지 마세요. 장문으로 자연스럽게 서술하세요.\n"
        f"선택된 스타일: {style_desc}, 요구 길이: {len_desc}"
    )
    return f"{shared}\n【네이버 블로그 전용 레이아웃】\n[첫 줄: 이목 집중형 제목]\n[본문: 1200자 이상의 수집된 뉴스 요약 팩트 중심 스토리텔링]\n[섹션: 저작권 프리 공식 출처 사진 가이드 5개]\n[마지막: 스마트블록 저격 태그 20개 이상 폭탄]"

# 실행 버튼 구동
if st.sidebar.button("✨ 플랫폼별 블로그 글 생성", type="primary"):
    if not api_key:
        st.error("API 키를 입력해주세요.")
    elif query == "데이터를 먼저 붙여넣어 주세요" or not query:
        st.error("시그널 복사 데이터를 왼쪽 창에 먼저 붙여넣고 키워드를 선택하세요.")
    elif not platforms:
        st.error("플랫폼을 하나 이상 선택해주세요.")
    else:
        # 붙여넣은 텍스트에서 선택한 키워드의 진짜 요약내용 매칭해서 가져오기
        factual_summary = keyword_data_map.get(query, "실시간 핵심 급상승 트렌드 뉴스")
        
        results = {}
        for p in platforms:
            with st.spinner(f"붙여넣으신 시그널 실제 뉴스 요약을 기반으로 '{p}' 상위 노출 원고 작성 중..."):
                sys_p = get_system_prompt(p, style, length)
                
                # 사용자가 복사해서 붙여넣은 진짜 뉴스 요약본을 AI 프롬프트에 쌩으로 주입!
                user_m = (
                    f"【사용자가 직접 시그널에서 복사해 온 실제 뉴스 요약 데이터】\n- 타겟 키워드: {query}\n- 뉴스 요약 및 맥락: {factual_summary}\n\n"
                    f"위의 요약 데이터에 명시된 팩트만을 완벽한 사실적 기반으로 삼아 글을 전개하세요. 절대 거짓 정보를 지어내지 마세요. "
                    f"이 이슈의 배경, 대중들의 실시간 반응 여론, 그리고 이 소식이 가진 사회적 파장을 자연스럽게 엮어 1,200자 이상의 아주 긴 본문을 구성해 주세요. "
                    f"상단 제목 강제 고정, 하단 스마트블록용 태그 20개 이상, 저작권 프리 사진 가이드 5개 조건을 무조건 준수하고, 본문 중간에 '**' 기호는 절대 노출 금지입니다."
                )
                
                res_content = call_ai_prime_tech(api_key, sys_p, user_m, selected_model)
                results[p] = res_content
                if "❌" not in res_content and "⚠️" not in res_content:
                    save_to_history(query, p, res_content)
        
        st.success("🎉 수집 팩트 기반 원고 생성 및 로컬 저장 완료!")
        tabs = st.tabs(platforms)
        for idx, p in enumerate(platforms):
            with tabs[idx]:
                st.markdown(f"### 🖥️ {p} 상위 노출 마스터 원고")
                st.text_area(f"{p} 결과물 (드래그 복사 가능)", value=results.get(p, ""), height=650, key=f"text_area_{p}")

# 과거 작성 기록 보관함 배치
st.sidebar.markdown("---")
st.sidebar.header("🗂️ 과거 작성 원고 보관함")

history_files = get_history_files()
if history_files:
    selected_file = st.sidebar.selectbox("📂 다시 열람할 원고 선택", history_files)
    if selected_file:
        file_path = os.path.join(HISTORY_DIR, selected_file)
        with open(file_path, "r", encoding="utf-8") as f:
            saved_content = f.read()
        st.markdown("---")
        st.subheader(f"📂 기록 보관함 열람: {selected_file}")
        st.text_area("보관된 원고 내용", value=saved_content, height=400, key="history_view_area")
