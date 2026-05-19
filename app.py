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
    
    payload = json.dumps({
        "model": model_name,
        "max_tokens": 3500,  # 분량이 길게 나올 수 있도록 맥스 토큰을 넉넉하게 확장
        "messages": [
            {"role": "user", "content": f"[System 규칙: {sys_prompt}]\n\n요청 과제: {user_msg}"}
        ]
    })
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {key}'
    }
    
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
                
        if not output_text.strip() and "text" in str(result_json):
            return f"⚠️ [안전 복구 로직 가동]\n\n{json.dumps(result_json, ensure_ascii=False, indent=2)}"
            
        return output_text.strip()
    except Exception as e:
        return f"❌ 데이터 분석 오류: {str(e)}"

def get_system_prompt(p, style_desc, len_desc):
    # [★ 프롬프트 엔진 개조] 별표(**), 화살표 등 AI 티 내는 기호를 원천 차단하고 분량을 강제하는 초강력 가이드라인 주입
    shared = (
        f"당신은 이웃들과 친근하게 소통하는 한국의 전문 탑블로거입니다. "
        f"반드시 다음의 세 가지 작성 규칙을 목숨 걸고 지키세요.\n"
        f"1. [기호 절대 금지]: 본문에 별표 기호(**), 샵 기호(#), 화살표(▶), 대괄호 등 AI가 작성한 티가 나는 모든 마크다운 서식 문자를 절대로 쓰지 마세요. 강조하고 싶다면 문맥이나 소제목 문장 자체로 강조하세요.\n"
        f"2. [인간적인 말투 채택]: '~했어요', '~했죠' 같은 기계적인 종결어미를 남발하지 말고, 실제 사람이 대화하듯 '안녕하세요 여러분!', '~인 것 같아요', '~하더라고요' 등 자연스럽고 흡입력 있는 구어체로 작성하세요.\n"
        f"3. [강제 분량 확장]: 글자 수를 채우기 위해 사건의 상세한 전말, 대중들의 실제 반응(긍정/부정), 앞으로 우리 사회에 미칠 영향과 전망까지 세부 카테고리를 나누어 깊이 있게 서술하세요. 최소 1,200자 이상의 풍성한 장문으로 빌드해야 합니다.\n"
        f"선택된 스타일: {style_desc}, 요구 길이: {len_desc}"
    )
    
    prompts = {
        "워드프레스": f"{shared}\n【워드프레스용 구조】 기호 없이 깔끔하게 제목, 메타 디스크립션, 그리고 대형 소제목 위주로 본문을 길게 서술하세요. 중간에 [📷 사진 추천 마크]를 넣어주세요.",
        "네이버 블로그": f"{shared}\n【네이버 블로그용 구조】 이웃에게 인사하며 시작하고, 각 문단이 3~4줄을 넘지 않도록 가독성 좋게 줄바꿈을 자주 하세요. 본문 하단에만 자연스러운 핵심 키워드 태그를 5개 내외로 적어주세요. 본문 한가운데에 특수기호(**, ▶)는 절대 금지입니다.",
        "티스토리": f"{shared}\n【티스토리용 구조】 깔끔하고 이성적인 톤을 유지하면서, 정보 전달력을 높이기 위해 문단을 세부적으로 쪼개어 장문으로 서술하세요. FAQ 섹션을 기호 없이 추가하세요."
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
            with st.spinner(f"AI가 인간 모드로 빙의하여 기호를 제거하고 '{p}' 원고를 풍성하게 집필 중입니다..."):
                sys_p = get_system_prompt(p, style, length)
                
                # 유저 프롬프트에서도 기호 삭제와 분량 확보를 재차 압박
                user_m = (
                    f"오늘 일어난 실시간 급상승 키워드인 '{query}'에 대한 뉴스 소식을 다룹니다. "
                    f"단순한 요약에 그치지 말고 관련된 비하인드 스토리와 네티즌들의 여론, 향후 사법적/사회적 파장까지 세밀하게 분석해서 "
                    f"텍스트 상자 안이 꽉 차도록 아주 길게 작성해 주세요. 본문 어디에도 '**' 나 '▶' 같은 기호가 들어가면 안 됩니다. "
                    f"오늘 날짜: {datetime.date.today().strftime('%Y-%m-%d')}"
                )
                
                results[p] = call_ai_prime_tech(api_key, sys_p, user_m, selected_model)
        
        st.success("🎉 인간형 최적화 블로그 원고 생산이 완료되었습니다!")
        tabs = st.tabs(platforms)
        for idx, p in enumerate(platforms):
            with tabs[idx]:
                st.markdown(f"### 🖥️ {p} 최적화 포스팅 원고 (기호 차단 버전)")
                st.text_area(f"{p} 결과물 (드래그 복사 가능)", value=results.get(p, ""), height=600, key=f"text_area_{p}")
