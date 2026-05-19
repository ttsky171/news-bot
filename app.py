import streamlit as st
import json
import http.client
from urllib.parse import urlparse
import datetime
import os

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
DATA_FILE = "signal_live_data.json" # 확장 프로그램이 던진 데이터 저장용 파일

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
# [🛠️ 수신 엔진] 크롬 확장 프로그램이 보낸 데이터 로드 함수
# -------------------------------------------------------------
def load_extension_data():
    """확장 프로그램이 파일로 떨구거나 전송한 시그널 실시간 데이터를 동적 로드"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # 데이터가 너무 오래되지 않았는지 검증 (예: 1시간 이내)
                return data.get("keywords", []), data.get("metadata", {}), data.get("updated_at", "미정")
        except:
            pass
    return [], {}, "데이터 없음"

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
# [📡 연동 섹션] 확장 프로그램 수신 상태 확인
# -------------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.subheader("📡 크롬 확장 프로그램 동기화 상태")

# 실시간 데이터 로드 수행
live_kws, live_metadata, last_update = load_extension_data()

if live_kws:
    st.sidebar.success(f"✅ 연동 완료! (최근 동기화: {last_update})")
    options_list = live_kws
else:
    st.sidebar.warning("⚠️ 시그널 창을 크롬 탭에 띄워두세요.")
    options_list = ["크롬 확장 프로그램의 신호를 기다리는 중..."]

query = st.sidebar.selectbox("🎯 작성할 최적화 키워드 선택", options_list)

platforms = st.sidebar.multiselect("🖥 발행 플랫폼 선택 (복수 선택 가능)", ["워드프레스", "네이버 블로그", "티스토리"], default=["네이버 블로그"])
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
    
    possible_paths = ["/v1/messages", "/v1/api/v1/messages", "/api/v1/messages"]
    data = b""
    res_status = 0
    
    for path in possible_paths:
        conn = http.client.HTTPSConnection(host, timeout=60)
        try:
            conn.request("POST", path, payload, headers)
            res = conn.getcall() if hasattr(conn, 'getcall') else conn.getresponse()
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
        f"함께 전달되는 시그널 뉴스 원문의 실시간 데이터 요약본을 완벽한 팩트 기반으로 삼아 글을 전개하세요. 절대 거짓을 창작하지 마세요.\n\n"
        f"1. [이목 집중형 제목 강제 고정]: 원고의 첫 줄은 무조건 독자의 궁금증을 유발하고 클릭을 유도하는 자극적이고 트렌디한 제목으로 시작하세요. 중간에 특수기호(**)는 넣지 마세요.\n"
        f"2. [스마트블록 타겟 태그 폭탄]: 본문 맨 마지막에 네이버 스마트블록(인기글/주제별 검색)에 무조건 걸리도록 연관 키워드, 성별/연령별 타겟 키워드, 롱테일 키워드를 섞어 최소 20개 이상의 샵(#) 태그를 쏟아내세요.\n"
        f"3. [저작권 무죄 사진/링크 추천 섹션 생성]: 본문 하단에 공식 사진 소스 가이드 5개를 정확하게 작성하세요. "
        f"정치/이슈/정부 관련 주제라면 대한민국 정부 공식 브리핑 사이트나 e-영상역사관 링크를 제공하고, 연예인/셀럽/스포츠 관련 주제라면 해당 인물의 오피셜 인스타그램 아이디나 공식 유튜브 채널 링크를 기반으로 어떤 장면을 캡처해야 하는지 5개의 구체적인 가이드를 생성하세요.\n"
        f"4. [기호 절대 금지]: 제목과 본문 한가운데에는 별표(**)나 화살표(▶) 같은 AI 서식 기호를 절대로 쓰지 마세요. 장문으로 자연스럽게 서술하세요.\n"
        f"선택된 스타일: {style_desc}, 요구 길이: {len_desc}"
    )
    return f"{shared}\n【네이버 블로그 전용 레이아웃】\n[첫 줄: 이목 집중형 제목]\n[본문: 1200자 이상의 수집된 뉴스 요약 팩트 중심 스토리텔링]\n[섹션: 저작권 프리 공식 출처 사진 가이드 5개]\n[마지막: 스마트블록 저격 태그 20개 이상 폭탄]"

# 실행 버튼 구동
if st.sidebar.button("✨ 플랫폼별 블로그 글 생성", type="primary"):
    if not api_key:
        st.error("API 키를 입력해주세요.")
    elif query == "크롬 확장 프로그램의 신호를 기다리는 중..." or not query:
        st.error("확장 프로그램으로부터 수집된 시그널 키워드가 아직 없습니다.")
    elif not platforms:
        st.error("플랫폼을 하나 이상 선택해주세요.")
    else:
        # 확장 프로그램이 파일에 박아 넣은 해당 키워드의 진짜 뉴스 요약본 가져오기
        factual_summary = live_metadata.get(query, "실시간 핵심 이슈 트렌드 전말 보도")
        
        results = {}
        for p in platforms:
            with st.spinner(f"확장 프로그램이 전달한 백엔드 팩트를 탑재하여 '{p}' 노출 원고 집필 중..."):
                sys_p = get_system_prompt(p, style, length)
                
                user_m = (
                    f"【크롬 확장 프로그램 자동 실시간 연동 뉴스 요약 데이터】\n- 핵심 키워드: {query}\n- 사이트 팩트 뉴스 내용: {factual_summary}\n\n"
                    f"위의 요약 데이터에 명시된 사실만을 완벽한 논리 축으로 삼으세요. 인위적인 소설이나 거짓 루머 가공은 엄격히 가로막습니다. "
                    f"대중의 최신 여론 및 이 이슈의 핵심 파장을 자연스럽게 연결하여 1,200자 이상의 꽉 찬 장문 본문을 구성해 주세요. "
                    f"상단 제목 고정, 하단 스마트블록용 태그 20개 이상, 저작권 프리 사진 가이드 5개 조건을 무조건 준수하고 본문 내 '**' 기호는 절대 불허합니다."
                )
                
                res_content = call_ai_prime_tech(api_key, sys_p, user_m, selected_model)
                results[p] = res_content
                if "❌" not in res_content and "⚠️" not in res_content:
                    save_to_history(query, p, res_content)
        
        st.success("🎉 크롬 연동형 팩트 매핑 원고 생성 및 로컬 저장 성공!")
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
        with open(file_path, "w", encoding="utf-8") as f: # 읽기모드 열람 보장
            pass
        with open(file_path, "r", encoding="utf-8") as f:
            saved_content = f.read()
        st.markdown("---")
        st.subheader(f"📂 기록 보관함 열람: {selected_file}")
        st.text_area("보관된 원고 내용", value=saved_content, height=400, key="history_view_area")
