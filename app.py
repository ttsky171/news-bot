import streamlit as st
import json
import http.client
import os
import datetime

# 페이지 설정
st.set_page_config(page_title="실시간 뉴스 블로그 생성기", page_icon="📰", layout="wide")

# 폴더 관리
HISTORY_DIR = "blog_history"
if not os.path.exists(HISTORY_DIR): 
    os.makedirs(HISTORY_DIR)

def save_to_history(keyword, platform, content):
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_keyword = "".join(c for c in keyword if c.isalnum() or c in (' ', '_', '-')).strip()
    filename = f"{HISTORY_DIR}/{now}_{safe_keyword}_{platform}.txt"
    with open(filename, "w", encoding="utf-8") as f: 
        f.write(content)

# 1. JSONBin 데이터 로드 (업데이트 시간 포함)
def load_extension_data():
    import urllib.request
    BIN_ID = "6a0c24886610dd3ae86c19cd"
    MASTER_KEY = "$2a$10$XJlSzhQ1AoOvMQqIH95KOeLDbr7ohp4ocKXh2V3iAJxHW.QvAnOm6"
    try:
        url = f"https://api.jsonbin.io/v3/b/{BIN_ID}"
        req = urllib.request.Request(url, headers={"X-Master-Key": MASTER_KEY})
        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            actual = res_data.get("record", {})
            return actual.get("keywords", []), actual.get("metadata", {}), actual.get("updated_at", "미정")
    except Exception:
        return [], {}, "연동 대기 중"

# 2. AI 호출 엔진
def call_ai_prime_tech(key, sys_prompt, user_msg, model_name):
    host = "aiprimetech.io"
    payload = json.dumps({
        "model": model_name,
        "max_tokens": 4000, 
        "messages": [{"role": "user", "content": f"[System 규칙: {sys_prompt}]\n\n{user_msg}"}]
    })
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {key}'}
    
    try:
        conn = http.client.HTTPSConnection(host, timeout=60)
        conn.request("POST", "/v1/messages", payload, headers)
        res = conn.getresponse()
        data = res.read().decode("utf-8")
        conn.close()
        
        result_json = json.loads(data)
        
        if "content" in result_json and len(result_json["content"]) > 0:
            return result_json["content"][0].get("text", "본문 텍스트가 비어있습니다.")
        elif "error" in result_json:
            return f"AI API 에러 발생: {result_json['error']}"
        else:
            return f"알 수 없는 응답 형식: {data}"
    except Exception as e:
        return f"통신 장애 발생: {str(e)}"

# 3. 화면 UI
st.title("📰 실시간 이슈 뉴스 블로그 글 생성기")

# 사이드바 설정
st.sidebar.header("🔑 설정 및 시그널")
api_key = st.sidebar.text_input("AI Prime Tech API Key", type="password")
model = st.sidebar.selectbox("모델 선택", ["claude-sonnet-4-6", "claude-opus-4-6"])

# 데이터 로드 및 시그널 타임스탬프 표시
live_kws, live_metadata, last_update = load_extension_data()

# [기능 1] 키워드 수집/도착 시각 안내
st.sidebar.info(f"🕒 실시간 키워드 연동 시각: {last_update}")

if not live_kws:
    live_kws = ["대기 중..."]
query = st.sidebar.selectbox("작성할 키워드 선택", live_kws)
platforms = st.sidebar.multiselect("발행 플랫폼", ["네이버 블로그", "티스토리"], default=["네이버 블로그"])
style = st.sidebar.selectbox("글 스타일", ["📰 뉴스 보도체", "😊 쉬운 설명체"])

# [기능 2] 글자 수 옵션 선택 UI 추가
length_option = st.sidebar.selectbox("목표 글자 수", ["공백 제외 1,000자 내외", "공백 제외 1,500자 내외", "공백 제외 2,000자 이상(상세히)"])

# 메인 생성 로직
if st.sidebar.button("✨ 글 생성하기", type="primary"):
    if not api_key:
        st.error("API 키를 입력하세요.")
    elif query == "대기 중..." or not query:
        st.error("작성할 유효한 키워드를 선택해주세요.")
    elif not platforms:
        st.warning("발행 플랫폼을 최소 하나 이상 선택해주세요.")
    else:
        factual_summary = live_metadata.get(query, "최신 정보 없음")
        
        # 플랫폼별 순회하며 생성
        for p in platforms:
            # 1. 스타일에 따른 톤앤매너
            tone_instruction = ""
            if style == "📰 뉴스 보도체":
                tone_instruction = "신뢰감 있고 객관적인 신문 기사 어조(~다, ~합니다)로 작성하세요. 자극적인 수식어는 배제하고 팩트 전달에 집중하세요."
            elif style == "😊 쉬운 설명체":
                tone_instruction = "친근한 블로그 어조(~에요, ~습니다)로 작성하세요. 독자가 이해하기 쉽게 비유를 섞어가며 친절하게 설명하세요. 적절한 이모지를 섞어주면 좋습니다."

            # 2. 플랫폼별 특성 반영
            platform_instruction = ""
            if p == "네이버 블로그":
                platform_instruction = (
                    "- 제목은 클릭을 부르는 매력적인 제목 3개를 추천해 주되, 그중 가장 좋은 것 하나를 본문 맨 위에 크게 배치하세요.\n"
                    "- 네이버 블로그 특성에 맞게 '서론-본문(소제목 분할)-결론(내 의견/맺음말)' 구조를 명확히 하세요.\n"
                    "- 가독성을 위해 문단을 자주 나누고, 중요한 키워드는 문맥 속에서 자연스럽게 강조되도록 하세요."
                )
            elif p == "티스토리":
                platform_instruction = (
                    "- SEO(검색엔진 최적화)에 최적화된 구글 친화적 구조로 작성하세요.\n"
                    "- 제목은 핵심 키워드가 맨 앞에 오는 명확한 제목 1개만 깔끔하게 작성하세요.\n"
                    "- 본문은 H2, H3 형태의 논리적인 소제목 구조를 갖추고, 정보의 깊이가 느껴지도록 서술하세요."
                )

            # 3. 종합 시스템 프롬프트 조립 (글자 수 및 [기능 3] 썸네일 규칙 포함)
            sys_prompt = (
                f"당신은 전문 파워블로거이자 카피라이터입니다. 제공된 요약 정보를 바탕으로 독자에게 유익하고 완성도 높은 글을 작성해야 합니다.\n\n"
                f"[톤앤매너 규칙]\n{tone_instruction}\n\n"
                f"[플랫폼별 작성 규칙]\n{platform_instruction}\n\n"
                f"[글자 수 제한 규칙]\n- 분량은 반드시 **{length_option}**에 맞추어 알차고 풍부한 정보량으로 채워주세요.\n\n"
                f"[⚡ 썸네일 추천 규칙]\n"
                f"- 글 작성이 모두 끝난 맨 마지막 줄에 '---' 구분선을 그은 후, [추천 썸네일 아이디어] 섹션을 만들어주세요.\n"
                f"- 이 글에 가장 잘 어울리는 이미지 썸네일 디자인 컨셉 1개와, 미드저니/DALL-E 같은 이미지 AI에 그대로 입력할 수 있는 영어 프롬프트(Prompt)를 1줄로 작성해 주세요.\n\n"
                f"[⚠️ 절대 금지 규칙]\n"
                f"- 본문 내에서 마크다운 강조 기호인 '**' (별표 두 개)는 절대 사용하지 마세요. (텍스트 강조 시 기호 없이 문맥으로 처리할 것)\n"
                f"- AI가 작성한 티가 나는 문구(예: 'AI 요약에 따르면', '아래는 요약 내용입니다')는 절대 넣지 마세요."
            )
            
            # 4. 사용자 메시지
            user_msg = (
                f"● 타겟 키워드: {query}\n"
                f"● 키워드 수집 시각: {last_update}\n"
                f"● 팩트 및 정보 요약:\n{factual_summary}\n\n"
                f"위 정보를 완벽히 녹여내어 독자들이 끝까지 읽을 수 있는 매력적인 블로그 포스팅과 썸네일 제안까지 완성해줘."
            )
            
            widget_key = f"txt_area_{p.replace(' ', '_')}"
            
            with st.spinner(f"[{p}] {length_option} 분량으로 글 및 썸네일 생성 중..."):
                content = call_ai_prime_tech(api_key, sys_prompt, user_msg, model)
                
                st.subheader(f"✨ {p} 결과물 ({style})")
                st.text_area("내용 (본문 + 맨 아래 썸네일 가이드 포함)", value=content, height=600, key=widget_key)
                
                # 오류 메시지가 아닌 정상 글일 때만 파일 저장
                if "통신 장애 발생" not in content and "AI API 에러" not in content:
                    save_to_history(query, p, content)
            
            st.divider()
