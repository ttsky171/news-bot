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
        "max_tokens": 4000,  # 태그 폭탄과 사진 가이드를 위해 맥스 토큰을 최대치로 확장
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
    # [상위노출 치트키 엔진 주입] 네이버 스마트블록과 트래픽 폭발을 위한 초정밀 구조 제어 프롬프트
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
        "네이버 블로그": f"{shared}\n【네이버 블로그 전용 레이아웃】\n[첫 줄: 이목 집중형 제목]\n[본문: 1200자 이상의 자연스러운 인간형 구어체 및 스토리텔링]\n[섹션: 저작권 프리 공식 출처 사진 가이드 5개 (정부사이트 또는 인스타 링크 포함)]\n[마지막: 스마트블록 저격 태그 20개 이상 폭탄]",
        "워드프레스": f"{shared}\n【워드프레스 전용】 기호 없이 고품질 HTML 구조로 가되, 상단 제목과 하단 태그 20개, 그리고 오피셜 사이트 이미지 소스 링크 5개를 정교하게 포함하세요.",
        "티스토리": f"{shared}\n【티스토리 전용】 가독성 높은 구성을 취하되 상단 낚시성 제목과 하단 20개 연관 태그, 오피셜 미디어 인용 가이드 5개를 엄격히 준수하세요."
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
                    f"현재 실시간 검색어 1위인 '{query}' 키워드를 완벽 분석하세요.\n"
                    f"독자가 끝까지 읽게 만드는 매끄러운 서론-본론-결론을 도출하고, "
                    f"내가 주문한 3가지 조건(상단 제목 고정, 하단 스마트블록용 태그 20개 이상, 저작권 프리 정부사이트/인스타그램 링크 포함 사진 가이드 5개)을 빠짐없이 꽉 채워서 장문으로 뽑아내세요. "
                    f"절대 본문 중간에 '**' 같은 AI 표식을 남기지 마세요. 오늘 날짜: {datetime.date.today().strftime('%Y-%m-%d')}"
                )
                
                results[p] = call_ai_prime_tech(api_key, sys_p, user_m, selected_model)
        
        st.success("🎉 스마트블록 저격형 고품질 원고 생산이 완료되었습니다!")
        tabs = st.tabs(platforms)
        for idx, p in enumerate(platforms):
            with tabs[idx]:
                st.markdown(f"### 🖥️ {p} 상위 노출 마스터 원고")
                st.text_area(f"{p} 결과물 (드래그 복사 가능)", value=results.get(p, ""), height=650, key=f"text_area_{p}")
