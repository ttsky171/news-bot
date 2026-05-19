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

st.title("📰 실시간 이슈 뉴스 블로그 글 생성기")
st.caption("AI 프라임텍 전용 클라우드 노드 구동 엔진 · 저작권 회피형 미디어 가이드 자동 맵핑")

# 사이드바 설정
st.sidebar.header("🔑 인증 및 옵션 설정")

# 시그널 실시간 검색어 사이트 바로가기 버튼 배치
st.sidebar.link_button("🔥 Signal.bz (시그널 실시간 검색어) 바로가기", "https://signal.bz")
st.sidebar.markdown("---")

api_key = st.sidebar.text_input("AI Prime Tech API Key 입력", type="password")
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

def call_ai_prime_tech(key, sys_prompt, user_msg):
    host = "aiprimetech.io"
    path = "/v1/messages"
    
    # [페이로드 최적화] 일부 대행 서버에서 꼬이는 툴 호출 구조를 완화하고, 
    # AI가 툴 사용 로그 뒤에 반드시 본문 텍스트를 이어 붙이도록 Max 토큰을 대폭 확장합니다.
    payload = json.dumps({
        "model": "claude-sonnet-4-6",
        "max_tokens": 4000, 
        "system": sys_prompt,
        "messages": [{"role": "user", "content": user_msg}],
        "tools": [{"type": "web_search_20250305", "name": "web_search"}]
    })
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {key}',
        'anthropic-version': '2023-06-01',
        'anthropic-dangerous-direct-browser-access': 'true'
    }
    
    conn = http.client.HTTPSConnection(host, timeout=120) # 검색 및 본문 작성을 위해 타임아웃 120초 확보
    try:
        conn.request("POST", path, payload, headers)
        res = conn.getresponse()
        data = res.read()
        
        if res.status != 200:
            return f"❌ 서버 응답 에러 (HTTP {res.status}): API 키나 충전 잔액을 확인하세요.\n상세 정보: {data.decode('utf-8', errors='ignore')}"
        
        result_json = json.loads(data.decode("utf-8"))
        content_list = result_json.get("content", [])
        
        output_text = ""
        
        # [방어형 파싱 알고리즘]
        # 툴 사용(tool_use) 결과 뒤에 숨어있는 순수 완성형 'text' 블록만 전부 이어 붙입니다.
        if isinstance(content_list, list):
            for block in content_list:
                if isinstance(block, dict):
                    # 표준 텍스트 블록인 경우 합산
                    if block.get("type") == "text":
                        output_text += block.get("text", "")
                    # 혹시나 대행 서버가 응답 구조를 커스텀해서 다른 키에 본문을 넣었을 경우 방어
                    elif "text" in block and block.get("type") != "tool_use":
                        output_text += block.get("text", "")
                        
        elif isinstance(content_list, dict):
            output_text = content_list.get("text", "")
            
        # [최종 강제 스크래핑 보완]
        # 위 필터링으로도 실패했는데 데이터 원본 어딘가에 글이 포함되어 있다면 JSON 전체에서 무식하게 글자만 긁어옵니다.
        if not output_text.strip():
            # JSON 껍데기 통째로 확인해서 대행 서버 원본 데이터를 화면에 복구 출력
            raw_str = json.dumps(result_json, ensure_ascii=False)
            if '"text":' in raw_str:
                return f"⚠️ [시스템 데이터 구조 강제 복구 가동]\n\n{json.dumps(result_json, ensure_ascii=False, indent=2)}"
            else:
                return "❌ [연동 실패] AI가 뉴스를 검색했으나 현재 사용 중인 API 서버(Gamsgo/프록시)가 최종 답변 단계를 전송하지 않고 끊었습니다. 이 경우 사이드바에서 '글 스타일'이나 '키워드'를 살짝 바꾸어 다시 실행해 보시거나, API 서버 측의 일시적 트래픽 초과 상태일 수 있습니다."
                
        return output_text.strip()
    except Exception as e:
        return f"❌ 통신 예외 발생: {str(e)}"
    finally:
        conn.close()

def get_system_prompt(p, style_desc, len_desc):
    # [프롬프트 가스라이팅 추가] AI에게 검색 툴(web_search) 사용 직후, 툴 일지만 남기지 말고 
    # '반드시 즉시 연속해서' 최종 블로그 완성 원고 본문을 작성하라고 강력하게 명령 명령을 심어놓습니다.
    shared = (
        f"당신은 한국 최고의 블로그 SEO 작가입니다. 반드시 web_search 툴을 사용해 최신 기사와 실시간 정보를 검색 및 전수 조사하세요. "
        f"그 후 검색 도구 사용에만 그치지 말고, 반드시 최종 사용자를 위한 완성된 블로그 원고 본문을 'text' 형태로 즉시 작성하여 응답에 포함해야 합니다. "
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
            with st.spinner(f"AI가 실시간 뉴스를 심층 검색하고 '{p}' 맞춤형 원고를 정밀 분석 중입니다. (약 10~20초 소요)..."):
                sys_p = get_system_prompt(p, style, length)
                # 유저 메시지에도 최종 텍스트 원고 생성을 재차 강조
                user_m = f"실시간 급상승 키워드인 '{query}' 소식을 구글/뉴스 웹 검색하여 팩트를 체크하고, 그 내용을 기반으로 완벽한 블로그 포스팅 원고를 최종 출력하세요. 본문 중간 적절한 곳에 [📷 사진 추천 1] 마크를 3개 이상 반드시 기입하세요. 오늘 날짜: {datetime.date.today().strftime('%Y-%m-%d')}"
                
                results[p] = call_ai_prime_tech(api_key, sys_p, user_m)
        
        st.success("🎉 실시간 뉴스 가동 및 원고 추출 연산이 완료되었습니다!")
        tabs = st.tabs(platforms)
        for idx, p in enumerate(platforms):
            with tabs[idx]:
                st.markdown(f"### 🖥️ {p} 최적화 포스팅 원고")
                st.text_area(f"{p} 결과물 (드래그 복사 가능)", value=results.get(p, ""), height=500, key=f"text_area_{p}")
