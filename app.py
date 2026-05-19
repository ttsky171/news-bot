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

# -------------------------------------------------------------
# [🔥 100% 리얼] Signal.bz 정밀 크롤링 엔진 (진짜 시그널 데이터만 수집)
# -------------------------------------------------------------
def fetch_pure_signal_keywords():
    """시그널 메인 페이지 HTML을 정밀 분석하여 현재 노출 중인 1~10위 실시간 검색어를 날것 그대로 파싱"""
    host = "signal.bz"
    path = "/"
    
    # 보안 방화벽을 속이기 위해 일반 크롬 브라우저의 접속 정보를 완벽하게 위장
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "max-age=0",
        "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1"
    }
    
    conn = http.client.HTTPSConnection(host, timeout=15)
    try:
        conn.request("GET", path, headers=headers)
        res = conn.getresponse()
        
        if res.status == 200:
            html = res.read().decode("utf-8", errors="ignore")
            
            # 시그널 사이트 고유의 실시간 키워드 감싸는 태그 구조 분석 패턴 기동
            # <span class="tx">키워드</span> 형태 추적
            raw_matches = re.findall(r'<span class="tx">([^<]+)</span>', html)
            
            final_keywords = []
            for kw in raw_matches:
                kw_clean = kw.strip()
                # 공백이나 숫자, 중복 제거 필터링
                if kw_clean and kw_clean not in final_keywords and not kw_clean.isdigit():
                    # 시그널 메뉴 탭 이름 같은 노이즈 필터링
                    if kw_clean in ["뉴스", "랭킹", "실시간 검색어", "로그인", "회원가입"]:
                        continue
                    final_keywords.append(kw_clean)
            
            # 상위 10개만 정확하게 컷트
            if final_keywords:
                return final_keywords[:10]
                
        # 만약 차단되거나 실패 시 사용자에게 알리기 위해 빈 배열 반환
        return []
    except:
        return []
    finally:
        conn.close()

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
st.caption("AI 프라임텍 전용 클라우드 노드 구동 엔진 · 시그널 실시간 동적 스크래핑 엔진")

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

st.sidebar.markdown("---")
st.sidebar.subheader("🔥 Signal.bz 리얼타임 수집기")

if "signal_real_kws" not in st.session_state:
    st.session_state["signal_real_kws"] = []

if st.sidebar.button("🔄 Signal.bz에서 진짜 실시간 순위 가져오기", type="primary"):
    with st.spinner("Signal.bz 웹서버에 직접 브라우저로 속여서 접속 중..."):
        real_data = fetch_pure_signal_keywords()
        if real_data:
            st.session_state["signal_real_kws"] = real_data
            st.sidebar.success(f"시그널 랭킹 {len(real_data)}개 수집 성공!")
        else:
            st.sidebar.error("❌ 시그널 방화벽이 차단했습니다. 잠시 후 다시 시도해 주세요.")

if st.session_state["signal_real_kws"]:
    options_list = st.session_state["signal_real_kws"]
else:
    options_list = ["새로고침 버튼을 눌러 시그널 데이터를 가져오세요"]

query = st.sidebar.selectbox("🎯 작성할 최적화 키워드 선택", options_list)

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
        f"전달받은 실시간 이슈 키워드를 기반으로 팩트를 정교하게 조사하여 왜곡 없이 인간이 쓴 것 같은 고품질 스토리텔링으로 원고를 전개하세요.\n\n"
        f"1. [이목 집중형 제목 강제 고정]: 원고의 첫 줄은 무조건 독자의 궁금증을 유발하고 클릭을 유도하는 자극적이고 트렌디한 제목으로 시작하세요. 중간에 특수기호(**)는 넣지 마세요.\n"
        f"2. [스마트블록 타겟 태그 폭탄]: 본문 맨 마지막에 네이버 스마트블록(인기글/주제별 검색)에 무조건 걸리도록 연관 키워드, 성별/연령별 타겟 키워드, 롱테일 키워드를 섞어 최소 20개 이상의 샵(#) 태그를 쏟아내세요.\n"
        f"3. [저작권 무죄 사진/링크 추천 섹션 생성]: 본문 하단에 블로거가 저작권 소송에 걸리지 않고 안전하게 쓸 수 있는 공식 사진 소스 가이드 5개를 정확하게 작성하세요. "
        f"정치/이슈/정부 관련 주제라면 대한민국 정부 브리핑룸 사이트 주소나 e-영상역사관 링크를 제공하고, 연예인/셀럽/스포츠 관련 주제라면 해당 인물의 오피셜 인스타그램 아이디나 공식 유튜브 채널 링크를 기반으로 어떤 장면을 캡처해야 하는지 5개의 구체적인 가이드를 생성하세요.\n"
        f"4. [기호 절대 금지]: 제목และ 본문 한가운데에는 별표(**)나 화살표(▶) 같은 AI 서식 기호를 절대로 쓰지 마세요. 장문으로 자연스럽게 서술하세요.\n"
        f"선택된 스타일: {style_desc}, 요구 길이: {len_desc}"
    )
    return f"{shared}\n【네이버 블로그 전용 레이아웃】\n[첫 줄: 이목 집중형 제목]\n[본문: 1200자 이상의 정보성 구어체 본문]\n[섹션: 저작권 프리 공식 출처 사진 가이드 5개]\n[마지막: 스마트블록 저격 태그 20개 이상 폭탄]"

# 실행 버튼 구동
if st.sidebar.button("✨ 플랫폼별 블로그 글 생성", type="primary"):
    if not api_key:
        st.error("API 키를 입력해주세요.")
    elif query == "새로고침 버튼을 눌러 시그널 데이터를 가져오세요" or not query:
        st.error("시그널 실시간 순위 새로고침 버튼을 먼저 눌러주세요.")
    elif not platforms:
        st.error("플랫폼을 하나 이상 선택해주세요.")
    else:
        results = {}
        for p in platforms:
            with st.spinner(f"시그널 진짜 키워드 '{query}' 분석 후 원고를 집필 중..."):
                sys_p = get_system_prompt(p, style, length)
                
                user_m = (
                    f"오늘 자 대한민국 실시간 급상승 키워드: '{query}'\n\n"
                    f"클로드는 이 키워드의 최신 뉴스 팩트와 정보, 대중들의 교차 여론을 스스로 크롤링 메모리에서 호출하여 절대로 왜곡 없이 팩트 기반으로 분석 글을 작성해야 합니다.\n"
                    f"네이버 스마트블록 검색 엔진이 가독성이 높다고 판단하도록 문단을 리드미컬하게 나누어 1,200자 이상의 아주 긴 원고를 구성하세요.\n"
                    f"상단 제목 강제 고정, 하단 스마트블록용 태그 20개 이상, 저작권 프리 사진 가이드 5개 조건을 100% 이행하고, 본문 내 '**' 기호는 절대로 노출하지 마세요."
                )
                
                res_content = call_ai_prime_tech(api_key, sys_p, user_m, selected_model)
                results[p] = res_content
                if "❌" not in res_content and "⚠️" not in res_content:
                    save_to_history(query, p, res_content)
        
        st.success("🎉 시그널 진짜 키워드 연동 원고 생성 완료 및 저장 성공!")
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
