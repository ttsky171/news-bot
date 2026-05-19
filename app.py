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
    
    # [웹 검색 활성화] 최신 뉴스를 검색하도록 tools 옵션을 다시 완벽하게 탑재합니다.
    payload = json.dumps({
        "model": "claude-sonnet-4-6",
        "max_tokens": 3000,
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
    
    conn = http.client.HTTPSConnection(host, timeout=90) # 검색 시간을 고려해 타임아웃을 90초로 늘림
    try:
        conn.request("POST", path, payload, headers)
        res = conn.getresponse()
        data = res.read()
        
        if res.status != 200:
            return f"❌ 서버 응답 에러 (HTTP {res.status}): API 키나 충전 잔액을 확인하세요.\n상세 정보: {data.decode('utf-8', errors='ignore')}"
        
        result_json = json.loads(data.decode("utf-8"))
        
        # [핵심 수정] 웹 검색 로그(tool_use 등)를 전부 걸러내고 순수 블로그 본문(text)만 누적 추출
        content_list = result_json.get("content", [])
        output_text = ""
        
        if isinstance(content_list, list):
            # content 배열을 돌면서 타입이 정확히 'text'인 블로그 완성 원고만 합칩니다.
            for block in content_list:
                if isinstance(block, dict) and block.get("type") == "text":
                    output_text += block.get("text", "")
                    
        elif isinstance(content_list, dict):
            if content_list.get("type") == "text":
                output_text = content_list.get("text", "")
        
        # 만약 필터링했는데도 본문이 비어있다면, 예외적으로 전체 응답에서 텍스트 데이터 강제 복구
        if not output_text.strip():
            if "text" in str(result_json):
                return f"⚠️ [안전 우회 추출 모드 실행]\n\n{json.dumps(result_json, ensure_ascii=False, indent=2)}"
            else:
                return "⚠️ AI가 웹 검색은 수행했으나 최종 블로그 원고 생산을 완료하지 못했습니다. 키워드를 변경하거나 잠시 후 다시 시도해 주세요."
                
        return output_text.strip()
    except Exception as e:
        return f"❌ 통신 예외 발생: {str(e)}"
    finally:
        conn.close()

def get_system_prompt(p, style_desc, len_desc):
    shared = f"당신은 한국 최고의 블로그 SEO 작가입니다. web_search 툴을 가동해 실시간 최신 뉴스나 정보를 분석한 후, 기사 원문 복사 없이 문장을 완벽히 재조합해 독창적인 글을 작성하세요. 스타일: {style_desc}, 길이: {len_desc}"
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
            # 웹 검색 시간이 추가되므로 안내 메시지 제공
            with st.spinner(f"AI가 실시간 뉴스를 검색하고 '{p}' 맞춤형 원고를 분석·생성 중입니다. 잠시만 기다려주세요..."):
                sys_p = get_system_prompt(p, style, length)
                user_m = f"실시간 급상승 키워드인 '{query}' 소식을 바탕으로 블로그 포스팅 원고를 빌드하세요. 본문 중간 적절한 곳에 [📷 사진 추천 1: 위치 및 오피셜 소스 인용 가이드] 마크를 3개 이상 반드시 기입하세요. 오늘 날짜: {datetime.date.today().strftime('%Y-%m-%d')}"
                
                # API 호출 후 저장
                results[p] = call_ai_prime_tech(api_key, sys_p, user_m)
        
        st.success("🎉 실시간 뉴스 검색 및 블로그 원고 생성이 완료되었습니다!")
        tabs = st.tabs(platforms)
        for idx, p in enumerate(platforms):
            with tabs[idx]:
                st.markdown(f"### 🖥️ {p} 최적화 포스팅 원고")
                st.text_area(f"{p} 결과물 (드래그 복사 가능)", value=results.get(p, ""), height=500, key=f"text_area_{p}")
