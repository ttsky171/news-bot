import streamlit as st
import json
import http.client
from urllib.parse import urlparse
import datetime

# 웹사이트 기본 레이아웃 테마 설정
st.set_page_config(page_title="실시간 뉴스 블로그 생성기", page_icon="📰", layout="wide")

st.markdown("""
    <style>
    .main {background-color: #0e1117; color: #fafafa;}
    div[data-baseweb="select"] {background-color: #1a1c23;}
    </style>
    """, unsafe_allow_html=True)

# -------------------------------------------------------------
# [기능] 브라우저 로컬 스토리지를 이용한 API Key 저장/불러오기 스크립트
# -------------------------------------------------------------
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

# 시그널 실시간 검색어 사이트 바로가기 버튼 배치
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
        # 앞자리 숫자 제거
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
    # [★ 중요 수정] ANTHROPIC_BASE_URL 규격에 맞게 엔드포인트 경로를 Anthropic 공식 API 주소 형태로 변환합니다.
    host = "aiprimetech.io"
    path = "/v1/api/v1/messages"  # 프록시 서버들이 공식 SDK 요청을 중계할 때 사용하는 표준 라우팅 경로로 변경
    
    payload = json.dumps({
        "model": model_name,
        "max_tokens": 3000, 
        "system": sys_prompt,
        "messages": [{"role": "user", "content": user_msg}]
    })
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {key}',  # ANTHROPIC_AUTH_TOKEN 역할을 수행
        'anthropic-version': '2023-06-01',
        'anthropic-dangerous-direct-browser-access': 'true'
    }
    
    conn = http.client.HTTPSConnection(host, timeout=60)
    try:
        conn.request("POST", path, payload, headers)
        res = conn.getresponse()
        data = res.read()
        
        # 만약 수정된 경로로도 에러(404 등)가 난다면 기존 경로로 재시도하는 자동 백업 로직 탑재
        if res.status == 404 or res.status == 400:
            conn.close()
            conn = http.client.HTTPSConnection(host, timeout=60)
            conn.request("POST", "/v1/messages", payload, headers)
            res = conn.getresponse()
            data = res.read()
            
        if res.status != 200:
            return f"❌ 서버 응답 에러 (HTTP {res.status}): API 키나 충전 잔액을 확인하세요.\n상세 정보: {data.decode('utf-8', errors='ignore')}"
        
        result_json = json.loads(data.decode("utf-8"))
        content_list = result_json.get("content", [])
        
        output_text = ""
        
        if isinstance(content_list, list):
            for block in content_list:
                if isinstance(block, dict) and block.get("type") == "text":
                    output_text += block.get("text", "")
        elif isinstance(content_list, dict):
            output_text = content_list.get("text", "")
            
        if not output_text.strip():
            if "text" in str(result_json):
                return f"⚠️ [우회 복구 성공]\n\n{json.dumps(result_json, ensure_ascii=False, indent=2)}"
            else:
                return f"❌ 대행 서버 경로 매칭 성공 및 연결 안정화되었으나, 현재 입력된 API 키의 잔액이 부족하거나 모델 권한이 닫혀 있습니다. 대시보드를 확인해 주세요."
                
        return output_text.strip()
    except Exception as e:
        return f"❌ 통신 예외 발생: {str(e)}"
    finally:
        conn.close()

def get_system_prompt(p, style_desc, len_desc):
    shared = (
        f"당신은 한국 최고의 블로그 SEO 작가입니다. 주어진 주제와 트렌드를 완벽하게 추론하고 분석하여, 기사 원문 복사 없이 문장을 완전히 새롭게 조합해 독창적인 글을 작성하세요. "
        f"스타일: {style_desc}, 길이: {len_desc}"
    )
    prompts = {
        "워드프레스": f"{shared}\n【워드프레스 전용 - HTML 태그 <h2> 사용】 출력 양식: [제목], [메타 디스크립션], [3번 방식 고유 썸네일 카피 가이드], [1, 2번 방식 저작권 무죄 소스 가이드], [본문] (중간에 [📷 사진 추천 마크] 3개 삽입)",
        "네이버 블로그": f"{shared}\n【네이버 블로그 전용 - 구어체 말투 준수】 출력 양식: [제목], [3번 방식 고유 썸네일 카피 가이드], [1, 2번 방식 저작권 프리 소스], [본문] (소제목 ▶ 사용 및 중간에 [📷 사진 추천 마크] 3개 삽입), [해시태그]",
        "티스토리": f"{shared}\n【티스토리 전용 - 마크다운 ## 사용】 출력 양식: [제목], [핵심 답변], [3번 방식 고유 썸네일 카피 가이드], [1, 2번 방식 저작권 프리 소스], [본문] (중간에 [📷 사진 추천 마크] 3개 삽입), [FAQ]"
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
            with st.spinner(f"AI({selected_model}) 엔진이 전용 게이트웨이를 통해 '{p}' 최적화 원고를 즉시 구성 중입니다..."):
                sys_p = get_system_prompt(p, style, length)
                user_m = f"실시간 급상승 핵심 키워드인 '{query}' 소식을 바탕으로 블로그 포스팅 원고를 빌드하세요. 본문 중간 적절한 곳에 [📷 사진 추천 1: 위치 및 오피셜 소스 인용 가이드] 마크를 3개 이상 반드시 기입하세요. 오늘 날짜: {datetime.date.today().strftime('%Y-%m-%d')}"
                
                results[p] = call_ai_prime_tech(api_key, sys_p, user_m, selected_model)
        
        st.success("🎉 블로그 원고 생산이 완료되었습니다!")
        tabs = st.tabs(platforms)
        for idx, p in enumerate(platforms):
            with tabs[idx]:
                st.markdown(f"### 🖥️ {p} 최적화 포스팅 원고")
                st.text_area(f"{p} 결과물 (드래그 복사 가능)", value=results.get(p, ""), height=500, key=f"text_area_{p}")
