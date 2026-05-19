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
    host = "aiprimetech.io"
    
    # [★ 초비상 방어 설정] 0.7x 우회 채널용 가상 페이로드 빌드
    # 대행사 서버가 OpenAI나 구형 프록시 규격으로 랩핑했을 확률에 대응하여 구조를 가장 심플하게 압축합니다.
    payload = json.dumps({
        "model": model_name,
        "max_tokens": 2500, 
        "messages": [
            {"role": "user", "content": f"[System 지시사항: {sys_prompt}]\n\n본문 작성 요청 주제: {user_msg}"}
        ]
    })
    
    # 0.7x 채널에서 충돌을 일으키는 anthropic-version 헤더 제거하고 대중적인 베이직 헤더만 전송
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {key}'
    }
    
    # 세 가지 대표적인 프록시 주소 경로를 순서대로 찔러보는 완전 자동 복구 루프 가동
    possible_paths = ["/v1/messages", "/v1/api/v1/messages", "/api/v1/messages"]
    data = b""
    res_status = 0
    
    for path in possible_paths:
        conn = http.client.HTTPSConnection(host, timeout=45)
        try:
            conn.request("POST", path, payload, headers)
            res = conn.getresponse()
            res_status = res.status
            data = res.read()
            if res_status == 200:
                break # 성공하면 루프 탈출
        except:
            pass
        finally:
            conn.close()
            
    if res_status != 200:
        return f"❌ 대행 서버 통신 실패 (HTTP {res_status}): API 키 그룹이나 잔액을 재점검하세요.\n반환 로그: {data.decode('utf-8', errors='ignore')[:300]}"

    try:
        result_json = json.loads(data.decode("utf-8"))
        
        # 구조 파싱 다각화 (공식형 / 대행사 변형 형태 전부 긁어모으기)
        output_text = ""
        
        # 1. Claude 표준 배열 구조 검사
        if "content" in result_json:
            c_list = result_json["content"]
            if isinstance(c_list, list):
                output_text = "".join([b.get("text", "") for b in c_list if isinstance(b, dict) and "text" in b])
            elif isinstance(c_list, dict):
                output_text = c_list.get("text", "")
        
        # 2. OpenAI 가상 변환 규격(choices) 구조 검사 (0.7x 그룹이 주로 쓰는 방식)
        elif "choices" in result_json:
            choices = result_json["choices"]
            if choices and isinstance(choices, list):
                msg_obj = choices[0].get("message", {})
                output_text = msg_obj.get("content", "")
                
        # 3. 그 외 다이렉트 텍스트 매핑 검사
        if not output_text.strip() and "text" in str(result_json):
            return f"⚠️ [안전 복구 로직 가동]\n\n{json.dumps(result_json, ensure_ascii=False, indent=2)}"
            
        if not output_text.strip():
            return "❌ 서버 연결은 완벽했으나, 0.7x 우회 채널에서 최종 원고 텍스트를 파싱하지 못했습니다. 대행사 사이트에서 API 키의 '그룹'을 배율이 없는 기본형으로 바꿀 수 있는지 확인해 보세요."
            
        return output_text.strip()
    except Exception as e:
        return f"❌ 데이터 분석 오류: {str(e)}"

def get_system_prompt(p, style_desc, len_desc):
    shared = (
        f"당신은 한국 최고의 블로그 SEO 작가입니다. 주어진 주제와 트렌드를 완벽하게 분석하여 기사 원문 복사 없이 문장을 완전히 새롭게 조합해 독창적인 글을 작성하세요. "
        f"스타일: {style_desc}, 길이: {len_desc}"
    )
    prompts = {
        "워드프레스": f"{shared}\n【워드프레스 전용 - HTML 태그 <h2> 사용】 출력 양식: [제목], [메타 디스크립션], [본문] (중간에 [📷 사진 추천 마크] 3개 삽입)",
        "네이버 블로그": f"{shared}\n【네이버 블로그 전용 - 구어체 말투 준수】 출력 양식: [제목], [본문] (소제목 ▶ 사용 및 중간에 [📷 사진 추천 마크] 3개 삽입), [해시태그]",
        "티스토리": f"{shared}\n【티스토리 전용 - 마크다운 ## 사용】 출력 양식: [제목], [본문] (중간에 [📷 사진 추천 마크] 3개 삽입), [FAQ]"
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
            with st.spinner(f"AI({selected_model}) 엔진이 전용 가성비 노드를 통해 '{p}' 원고를 최종 연산 중..."):
                sys_p = get_system_prompt(p, style, length)
                user_m = f"실시간 핵심 키워드인 '{query}' 소식을 바탕으로 블로그 포스팅 원고를 빌드하세요. 본문 중간 적절한 곳에 [📷 사진 추천] 마크를 3개 이상 반드시 기입하세요. 오늘 날짜: {datetime.date.today().strftime('%Y-%m-%d')}"
                
                results[p] = call_ai_prime_tech(api_key, sys_p, user_m, selected_model)
        
        st.success("🎉 블로그 원고 생산 공정이 완료되었습니다!")
        tabs = st.tabs(platforms)
        for idx, p in enumerate(platforms):
            with tabs[idx]:
                st.markdown(f"### 🖥️ {p} 최적화 포스팅 원고")
                st.text_area(f"{p} 결과물 (드래그 복사 가능)", value=results.get(p, ""), height=500, key=f"text_area_{p}")
