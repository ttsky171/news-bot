import streamlit as st
import json
import http.client
import os
import datetime
import glob

# 페이지 설정
st.set_page_config(page_title="실시간 뉴스 블로그 생성기", page_icon="📰", layout="wide")

# 폴더 관리
HISTORY_DIR = "blog_history"
if not os.path.exists(HISTORY_DIR): 
    os.makedirs(HISTORY_DIR)

# 세션 상태 초기화
if "generated_content" not in st.session_state:
    st.session_state.generated_content = {}
if "selected_keyword" not in st.session_state:
    st.session_state.selected_keyword = ""

def save_to_history(keyword, platform, content):
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_keyword = "".join(c for c in keyword if c.isalnum() or c in (' ', '_', '-')).strip()
    filename = f"{HISTORY_DIR}/{now}_{safe_keyword}_{platform}.txt"
    with open(filename, "w", encoding="utf-8") as f: 
        f.write(content)

# 1. JSONBin 데이터 로드 (시그널 연동 통로)
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

# 3. 화면 UI 및 사이드바 설정
st.title("📰 실시간 이슈 뉴스 블로그 글 생성기")

st.sidebar.header("🔑 설정 및 시그널")
api_key = st.sidebar.text_input("AI Prime Tech API Key", type="password")
model = st.sidebar.selectbox("모델 선택", ["claude-sonnet-4-6", "claude-opus-4-6"])

st.sidebar.markdown("[🔗 시그널 실시간 트렌드 사이트 바로가기](https://signal.bz/)")

live_kws, live_metadata, last_update = load_extension_data()
st.sidebar.info(f"🕒 시그널 데이터 연동 시각: {last_update}")

# [💡 핵심 수정 기능] 키워드 입력 모드 선택 (자동 연동 vs 직접 입력)
input_mode = st.sidebar.radio("키워드 선택 방식", ["🔄 시그널 실시간 연동", "✍️ 직접 수동 입력"])

if input_mode == "🔄 시그널 실시간 연동":
    if not live_kws:
        st.sidebar.warning("연동된 키워드가 없습니다. 직접 입력을 이용해 주세요.")
        final_query = ""
    else:
        final_query = st.sidebar.selectbox("작성할 키워드 선택", live_kws)
else:
    # 직접 입력 모드일 때 텍스트 인풋창 활성화
    final_query = st.sidebar.text_input("✍️ 키워드 직접 입력", placeholder="예: 아이폰18 출시일, 부동산 정책 발표")

platforms = st.sidebar.multiselect("발행 플랫폼", ["네이버 블로그", "티스토리", "워드프레스"], default=["네이버 블로그"])

style = st.sidebar.selectbox("글 스타일", [
    "📰 뉴스 보도체 (객관적, 사실 중심)", 
    "😊 쉬운 설명체 (친근함, 이모지 활용)",
    "🔥 이슈 분석체 (전문가 관점, 비판적 분석)",
    "✍️ 스토리텔링체 (부드러운 이야기 형식, 몰입감)"
])

length_option = st.sidebar.selectbox("목표 글자 수", ["공백 제외 1,000자 내외", "공백 제외 1,500자 내외", "공백 제외 2,000자 이상(상세히)"])

st.sidebar.divider()

# 과거 생성 기록 조회
st.sidebar.subheader("📂 과거 생성 기록 조회")
history_files = glob.glob(f"{HISTORY_DIR}/*.txt")
if history_files:
    history_files.sort(key=os.path.getmtime, reverse=True)
    file_names = [os.path.basename(f) for f in history_files]
    selected_file = st.sidebar.selectbox("기록된 파일 선택", ["선택 안 함"] + file_names)
    
    if selected_file != "선택 안 함":
        with open(f"{HISTORY_DIR}/{selected_file}", "r", encoding="utf-8") as f:
            history_content = f.read()
        st.sidebar.text_area("📄 기록된 본문 내용", value=history_content, height=250)
else:
    st.sidebar.caption("생성된 히스토리 기록이 아직 없습니다.")


# --- 메인 탭 구조 ---
tab1, tab2 = st.tabs(["✨ 포스팅 생성기", "📂 전체 히스토리 보관함"])

with tab1:
    # [💡 핵심 수정 기능] 직접 입력 모드일 때는 팩트 요약본도 유저가 직접 커스텀할 수 있게 메인 화면에 노출
    if input_mode == "✍️ 직접 수동 입력":
        st.subheader("📝 뉴스 참고 내용 직접 입력")
        custom_summary = st.text_area(
            "AI가 참고할 실시간 뉴스 내용이나 핵심 팩트를 적어주세요.", 
            placeholder="예시: 정부에서 내년부터 청년 주거 지원금을 월 50만 원으로 인상한다고 발표했다. 대상은 중위소득 120% 이하의 만 19세~34세 청년이다. 신청은 7월부터 시작된다.",
            height=150
        )
    else:
        # 자동 연동 모드일 때는 기존 데이터베이스에서 매칭
        custom_summary = live_metadata.get(final_query, "최신 정보 없음")
        st.info(f"📋 **현재 선택된 시그널 팩트 요약본:**\n{custom_summary}")

    st.write("") # 간격 띄우기

    # 1단계: 글 생성하기 버튼
    if st.button("🚀 1단계: 블로그 글 생성하기", type="primary"):
        if not api_key:
            st.error("API 키를 입력하세요.")
        elif not final_query or final_query.strip() == "":
            st.error("작성할 키워드를 선택하거나 직접 입력해 주세요.")
        elif input_mode == "✍️ 직접 수동 입력" and not custom_summary.strip():
            st.error("AI가 참고할 뉴스 내용(팩트)을 입력해 주세요.")
        elif not platforms:
            st.warning("발행 플랫폼을 최소 하나 이상 선택해주세요.")
        else:
            st.session_state.selected_keyword = final_query
            st.session_state.generated_content = {} 
            
            for p in platforms:
                # 톤앤매너 분기
                tone_instruction = ""
                if "뉴스 보도체" in style:
                    tone_instruction = "신뢰감 있고 객관적인 신문 기사 어조(~다, ~합니다)로 작성하세요. 주관적 감정은 배제하고 팩트 전달에 집중하세요."
                elif "쉬운 설명체" in style:
                    tone_instruction = "친근한 블로그 어조(~에요, ~습니다)로 작성하세요. 독자가 이해하기 쉽게 비유를 쓰고 적절한 이모지를 활용하세요."
                elif "이슈 분석체" in style:
                    tone_instruction = "날카로운 평론가/전문가 어조로 작성하세요. 사건의 배경, 원인, 향후 미칠 파장이나 전망까지 입체적으로 분석해야 합니다."
                elif "스토리텔링체" in style:
                    tone_instruction = "독자가 소설이나 에세이를 읽듯 몰입할 수 있도록 서두를 열고 징검다리식 전개 방식을 사용하여 부드럽게 서술하세요."

                # 플랫폼별 특성 반영
                platform_instruction = ""
                if p == "네이버 블로그":
                    platform_instruction = (
                        "- 제목은 클릭을 부르는 매력적인 제목 3개를 추천해 주되, 그중 가장 좋은 것 하나를 본문 맨 위에 크게 배치하세요.\n"
                        "- '서론-본문(소제목 분할)-결론(내 의견/맺음말)' 구조를 명확히 하세요.\n"
                        "- 문단을 자주 나누고 키워드가 자연스럽게 스며들도록 하세요."
                    )
                elif p == "티스토리":
                    platform_instruction = (
                        "- 구글 SEO 친화적인 구조로, 제목은 핵심 키워드가 맨 앞에 오는 명확한 제목 1개만 상단에 배치하세요.\n"
                        "- 본문은 대제목, 소제목 구조(H2, H3 스타일 문맥)를 확실히 지켜 논리적으로 작성하세요."
                    )
                elif p == "워드프레스":
                    platform_instruction = (
                        "- 전 세계 및 구글 통합 검색에 최적화된 웹 표준 포맷으로 작성하세요.\n"
                        "- 글 맨 처음에 '요약(Snippet)' 문단을 한 줄로 명확하게 넣어 가독성을 높이세요.\n"
                        "- 소제목 구분을 완벽히 하고, 문장 간결성을 유지하여 가독성을 극대화하세요."
                    )

                # 종합 프롬프트 조립
                sys_prompt = (
                    f"당신은 실시간 트렌드 전문 파워블로거이자 디지털 카피라이터입니다. 입력된 타겟 키워드와 "
                    f"뉴스 맥락 데이터를 완벽히 결합하여 대중의 관심사에 딱 맞는 깊이 있는 글을 작성해야 합니다.\n\n"
                    f"[톤앤매너 규칙]\n{tone_instruction}\n\n"
                    f"[플랫폼별 작성 규칙]\n{platform_instruction}\n\n"
                    f"[글자 수 제한 규칙]\n- 분량은 반드시 **{length_option}**에 맞추어 알차게 채워주세요.\n\n"
                    f"[🔗 팩트 기반 이미지/링크 출처 수집 규칙]\n"
                    f"- 만약 이 키워드가 '연예인, 셀럽, 아이돌, 스포츠 스타, 인플루언서' 관련 뉴스라면, 글의 하단에 관련된 해당 인물의 공식 인스타그램(Instagram) 링크나 소속사 공식 사이트 링크를 안내하여 독자가 고화질 사진을 합법적으로 확인하고 다운로드받을 수 있게 경로를 열어주세요.\n"
                    f"- 만약 이 키워드가 '정부 정책, 나라 일, 경제, 사회 법안, 공공 데이터, 부동산 정책' 관련 뉴스라면, 글 하단에 대한민국 정부 브리핑실, 혹은 관련 정부 부처(기재부, 국토부 등) 공식 행정 사이트의 직접 다운로드 가능한 경로 정보나 링크 예시를 명확히 포함시켜 신뢰도를 높여주세요.\n"
                    f"- 추가로 본문 중간중간에 쓰기 좋은 저작권 없는 무료 이미지 사이트(Unsplash, Pixabay) 추천 검색 키워드 팁도 포함해 주세요.\n\n"
                    f"[⚠️ 절대 금지 규칙]\n"
                    f"- 본문 내에서 마크다운 강조 기호인 '**' (별표 두 개)는 절대 사용하지 마세요.\n"
                    f"- 'AI 요약에 따르면' 같은 인위적인 문구는 절대 금지합니다. 직접 취재하고 분석한 트렌드 전문가처럼 작성하세요."
                )
                
                user_msg = (
                    f"● 실시간 트렌드 키워드: {final_query}\n"
                    f"● 뉴스 맥락 및 참고 팩트 정보:\n{custom_summary}\n\n"
                    f"위 수집 데이터와 뉴스 맥락을 철저히 분석하여 대중들이 열광하고 유익해할 완성도 높은 포스팅을 작성해줘. "
                    f"글 하단에는 조건에 맞는 공식 사진/정보 다운로드 링크 가이드라인도 잊지 말고 포함해줘."
                )
                
                with st.spinner(f"[{p}] {style} 스타일에 맞춰 글을 생성하는 중..."):
                    content = call_ai_prime_tech(api_key, sys_prompt, user_msg, model)
                    if "통신 장애 발생" not in content and "AI API 에러" not in content:
                        st.session_state.generated_content[p] = content
                        save_to_history(final_query, p, content)
                    else:
                        st.error(f"[{p}] 생성 오류: {content}")

    # 생성된 결과물 화면 출력
    if st.session_state.generated_content:
        st.success("🎉 선택한 플랫폼의 블로그 글 생성이 완료되었습니다!")
        
        for p, content in st.session_state.generated_content.items():
            widget_key = f"main_txt_{p.replace(' ', '_')}"
            st.subheader(f"✨ {p} 결과물")
            st.text_area("본문 내용", value=content, height=500, key=widget_key)
        
        st.divider()
        st.subheader("🖼️ 2단계: 썸네일 생성하기")
        st.info("위 본문 내용을 바탕으로 디자인 컨셉과 미드저니/DALL-E용 영어 프롬프트를 생성합니다.")
        
        if st.button("🎨 썸네일 컨셉 & 이미지 프롬프트 만들기", type="secondary"):
            with st.spinner("AI가 포스팅 맞춤형 썸네일 프롬프트를 기획 중입니다..."):
                thumb_sys_prompt = "당신은 전문 그래픽 디자이너입니다. 제공되는 블로그 본문을 분석하여, 유튜브 및 블로그에 가장 어울리는 트렌디한 썸네일 배치를 기획하고, 이미지 생성 AI(DALL-E 3, Midjourney)에 바로 넣을 수 있는 고품질 영어 프롬프트를 추출해내야 합니다."
                
                base_content = list(st.session_state.generated_content.values())[0]
                thumb_user_msg = f"실시간 키워드: {st.session_state.selected_keyword}\n\n이 글을 대표할 수 있는 썸네일 이미지 디자인을 기획해줘. 결과물에는 [썸네일 디자인 설명]과, 복사해서 쓸 수 있는 [AI 이미지 생성용 영어 프롬프트(English Prompt)]가 명확히 들어가야 해."
                
                thumb_result = call_ai_prime_tech(api_key, thumb_sys_prompt, thumb_user_msg, model)
                
                st.write("### 💡 추천 썸네일 제작 가이드")
                st.info(thumb_result)

# --- 탭 2: 전체 히스토리 보관함 ---
with tab2:
    st.subheader("📚 과거에 생성된 모든 글 보관소")
    all_files = glob.glob(f"{HISTORY_DIR}/*.txt")
    if all_files:
        all_files.sort(key=os.path.getmtime, reverse=True)
        for f_path in all_files:
            f_name = os.path.basename(f_path)
            with st.expander(f"📄 {f_name}"):
                with open(f_path, "r", encoding="utf-8") as f:
                    st.text_area("내용", value=f.read(), height=300, key=f"tab2_{f_name}")
    else:
        st.info("저장된 과거 글 기록이 없습니다.")
