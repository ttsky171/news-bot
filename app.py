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

# -------------------------------------------------------------
# [기능] 원고 저장을 위한 로컬 폴더 생성 및 관리 함수
# -------------------------------------------------------------
HISTORY_DIR = "blog_history"
if not os.path.exists(HISTORY_DIR):
    os.makedirs(HISTORY_DIR)

def save_to_history(keyword, platform, content):
    """생성된 원고를 파일로 저장하는 함수"""
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    # 파일명에 불필요한 공백이나 특수문자 제거
    safe_keyword = "".join(c for c in keyword if c.isalnum() or c in (' ', '_', '-')).strip()
    filename = f"{HISTORY_DIR}/{now}_{safe_keyword}_{platform}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

def get_history_files():
    """저장된 원고 파일 목록을 가져오는 함수"""
    files = [f for f in os.listdir(HISTORY_DIR) if f.endswith(".txt")]
    # 최신 글이 맨 위로 오도록 정렬
    files.sort(reverse=True)
    return files

# 브라우저 로컬 스토리지를 이용한 API Key 저장/불러오기
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
st.caption("AI 프라임텍 전용 클라우드 노드 구동 엔진 · 저작권 회피형 미디어 가이드 자동 맵핑")

# 사이드바 설정
st.sidebar.header("🔑 인증 및 옵션 설정")
st.sidebar.link_button("🔥 Signal.bz (시그널 실시간 검색어) 바로가기", "https://signal.bz")
st.sidebar.markdown("---")

# 세션 상태 확인 및 입력창 연동
if st.session_state["api_key_saved"]:
    default_key = st.session_state["api_key_saved"]
else:
    default_key = ""

api_key = st.sidebar.text_input("AI Prime Tech API Key 입력", value=default_key, type="password")

if api_key and api_key != st.session_state["api_key_saved"]:
    st.session_state["api_key_saved"] = api_key
    st.markdown(
        f"""
        <script>
        localStorage.setItem("prime_tech_api_key", "{api_key}");
        </script>
        """,
        unsafe_allow_html=True
    )

# 대행 서버 제공 모델 선택
selected_model = st.sidebar.selectbox(
    "🤖 Claude 모델 선택", 
    ["claude-sonnet-4-6", "claude-opus-4-6", "claude-opus-4-7"],
    index=0
)

raw_text = st.sidebar.text_area("🔥 Signal.bz 순위 통째로 복사·붙여넣기", height=150, 
                               placeholder="1 유재석 캠프\n2 어린이날...")

# 순위 텍스트 파싱
keywords = []
if raw_text:
    for line in raw_text.split('\n'):
        clean = line.strip()
        if not clean: continue
        for word in clean.split():
            if word.isdigit():
                clean = clean.replace(word, "", 1).strip()
        if clean and clean not in keywords:
            keywords.append(clean)

if keywords:
    query = st.sidebar.selectbox("🎯 작성할 최적화 키워드 선택", keywords)
else:
    query = st.sidebar.selectbox("🎯 작성할 최적화 키워드 선택", ["순위를 먼저 입력하세요"])

platforms = st.sidebar.multiselect("🖥 발행 플랫폼 선택 (복수 선택 가능)", ["워드프레스", "네이버 블로그", "티스토리"], default=["네이버 블로그"])
style = st.sidebar.selectbox("✍️ 글 스타일", ["📰 뉴스 보도체", "😊 쉬운 설명체", "💬 분석/의견체", "⚡ 짧은 요약체"])
length = st.sidebar.selectbox("📏 글 길이", ["짧게 (500자)", "보통 (1000자)", "길게 (2000자)"])

def call_ai_prime_tech(key, sys_prompt, user_msg, model_name):
    host = "aiprimetech.io"
    payload = json.dumps({
        "model": model_name,
        "max_tokens": 4000, 
        "messages": [
            {"role": "user", "content": f"[System 규칙: {sys_prompt}]\n\n요청 과제: {user_msg}"}
        ]
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
        return f"❌ 대행 서버 통신 실패 (HTTP {res_status}): API 키 그룹이나 잔액을 재점검하세요.\n반환 로그: {data.decode('utf-8', errors='ignore')[:300]}"

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
        f"다음 지시사항은 블로그 생존과 직결되니 무조건 완벽하게 이행하세요.\n\n"
        f"1. [이목 집중형 제목 강제 고정]: 원고의 첫 줄은 무조건 독자의 궁금증을 유발하고 클릭을 유도하는 자극적이고 트렌디한 제목으로 시작하세요. 중간에 특수기호(**)는 넣지 마세요.\n"
        f"2. [스마트블록 타겟 태그 폭탄]: 본문 맨 마지막에 네이버 스마트블록(인기글/주제별 검색)에 무조건 걸리도록 연관 키워드, 성별/연령별 타겟 키워드, 롱테일 키워드를 섞어 최소 20개 이상의 샵(#) 태그를 쏟아내세요.\n"
        f"3. [저작권 무죄 사진/링크 추천 섹션 생성]: 본문 하단에 블로거가 저작권 소송에 걸리지 않고 안전하게 쓸 수 있는 공식 사진 소스 가이드 5개를 정확하게 작성하세요. "
        f"만약 정치/이슈/정부 관련 주제라면 대한민국 청와대, 국회, 국방부 등 공식 정부 사이트 주소나 e-영상역사관 링크를 제공하고, 연예인/셀럽/스포츠 관련 주제라면 해당 인물의 오피셜 인스타그램 아이디나 공식 유튜브 채널 링크를 기반으로 어떤 장면을 캡처해야 하는지 5개의 구체적인 마크를 생성하세요.\n"
        f"4. [기호 절대 금지]: 제목과 본문 한가운데에는 별표(**)나 화살표(▶) 같은 AI 서식 기호를 절대로 쓰지 마세요. 장문으로 자연스럽게 서술하세요.\n"
        f"선택된 스타일: {style_desc}, 요구 길이: {len_desc}"
    )
    prompts = {
        "네이버 블로그": f"{shared}\n【네이버 블로그 전용 레이아웃】\n[첫 줄: 이목 집중형 제목]\n[본문: 1200자 이상의 자연스러운 인간형 구어체 및 스토리텔링]\n[섹션: 저작권 프리 공식 출처 사진 가이드 5개]\n[마지막: 스마트블록 저격 태그 20개 이상 폭탄]",
        "워드프레스": f"{shared}\n【워드프레스 전용】 상단 제목과 하단 태그 20개, 이미지 소스 링크 5개를 포함하세요.",
        "티스토리": f"{shared}\n【티스토리 전용】 상단 낚시성 제목과 하단 20개 연관 태그, 이미지 인용 가이드 5개를 포함하세요."
    }
    return prompts.get(p, shared)

# 실행 버튼 구동
if st.sidebar.button("✨ 플랫폼별 블로그 글 생성", type="primary"):
    if not api_key:
        st.error("API 키를 입력해주세요.")
    elif query == "순위를 먼저 입력하세요" or not query:
        st.error("작성할 키워드를 선택해주세요.")
    elif not platforms:
        st.error("플랫폼을 하나 이상 선택해주세요.")
    else:
        results = {}
        for p in platforms:
            with st.spinner(f"AI가 네이버 스마트블록 가이드라인에 맞춰 '{p}' 타겟 원고를 굽는 중..."):
                sys_p = get_system_prompt(p, style, length)
                user_m = (
                    f"현재 실시간 검색어인 '{query}' 키워드를 완벽 분석하세요.\n"
                    f"내가 주문한 3가지 조건(상단 제목 고정, 하단 스마트블록용 태그 20개 이상, 저작권 프리 정부사이트/인스타그램 링크 포함 사진 가이드 5개)을 빠짐없이 꽉 채워서 장문으로 뽑아내세요. "
                    f"절대 본문 중간에 '**' 같은 AI 표식을 남기지 마세요. 오늘 날짜: {datetime.date.today().strftime('%Y-%m-%d')}"
                )
                res_content = call_ai_prime_tech(api_key, sys_p, user_m, selected_model)
                results[p] = res_content
                
                # [기능 추가] 생성이 완료되는 즉시 로컬 파일로 영구 저장
                if "❌" not in res_content and "⚠️" not in res_content:
                    save_to_history(query, p, res_content)
        
        st.success("🎉 스마트블록 저격형 원고 생산 완료 및 로컬 저장소 백업 성공!")
        tabs = st.tabs(platforms)
        for idx, p in enumerate(platforms):
            with tabs[idx]:
                st.markdown(f"### 🖥️ {p} 상위 노출 마스터 원고")
                st.text_area(f"{p} 결과물 (드래그 복사 가능)", value=results.get(p, ""), height=650, key=f"text_area_{p}")

# -------------------------------------------------------------
# [기능 추가] 사이드바 맨 하단에 과거 작성 기록 보관함 배치
# -------------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.header("🗂️ 과거 작성 원고 보관함")

history_files = get_history_files()
if history_files:
    selected_file = st.sidebar.selectbox("📂 다시 열람할 원고 선택", history_files)
    if selected_file:
        file_path = os.path.join(HISTORY_DIR, selected_file)
        with open(file_path, "r", encoding="utf-8") as f:
            saved_content = f.read()
        
        # 사이드바에서 선택하면 메인 화면 하단에 열람 창을 띄워줌
        st.markdown("---")
        st.subheader(f"📂 기록 보관함 열람: {selected_file}")
        st.text_area("보관된 원고 내용 (드래그 복사 가능)", value=saved_content, height=400, key="history_view_area")
else:
    st.sidebar.caption("아직 저장된 기록이 없습니다. 글을 생성하면 여기에 차곡차곡 쌓입니다!")
