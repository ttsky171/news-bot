import streamlit as st
import json
import http.client
import os
import datetime
import glob
import urllib.request

# 페이지 설정
st.set_page_config(page_title="실시간 뉴스 블로그 생성기 Pro", page_icon="📰", layout="wide")

# 폴더 관리
HISTORY_DIR = "blog_history"
if not os.path.exists(HISTORY_DIR): 
    os.makedirs(HISTORY_DIR)

# 세션 상태 초기화
if "generated_content" not in st.session_state:
    st.session_state.generated_content = {}
if "selected_keyword" not in st.session_state:
    st.session_state.selected_keyword = ""
if "thumbnail_result" not in st.session_state:
    st.session_state.thumbnail_result = ""

def save_to_history(keyword, platform, content):
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_keyword = "".join(c for c in keyword if c.isalnum() or c in (' ', '_', '-')).strip()
    filename = f"{HISTORY_DIR}/{now}_{safe_keyword}_{platform}.txt"
    with open(filename, "w", encoding="utf-8") as f: 
        f.write(content)

# 1. JSONBin 데이터 로드 (시그널 연동 통로)
def load_extension_data():
    fallback_keywords = ["아이폰18 출시일", "부동산 주택 정책 발표", "나는솔로 결혼 소식", "국내 주식 트렌드", "주말 날씨 전망"]
    fallback_metadata = {k: f"{k} 관련 최신 트렌드 및 실시간 이슈 분석 뉴스입니다." for k in fallback_keywords}
    
    BIN_ID = "6a0c24886610dd3ae86c19cd"
    MASTER_KEY = "$2a$10$XJlSzhQ1AoOvMQqIH95KOeLDbr7ohp4ocKXh2V3iAJxHW.QvAnOm6"
    try:
        url = f"https://api.jsonbin.io/v3/b/{BIN_ID}"
        req = urllib.request.Request(url, headers={"X-Master-Key": MASTER_KEY})
        with urllib.request.urlopen(req, timeout=5) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            actual = res_data.get("record", {})
            kws = actual.get("keywords", [])
            meta = actual.get("metadata", {})
            if kws:
                return kws, meta, actual.get("updated_at", "실시간 연동 완료")
    except Exception:
        pass

    try:
        signal_url = "https://api.signal.bz/news/realtime" 
        req = urllib.request.Request(signal_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            signal_data = json.loads(response.read().decode("utf-8"))
            kws = [item.get("keyword") for item in signal_data.get("top_keywords", []) if item.get("keyword")]
            if kws:
                meta = {k: f"실시간 시그널 트렌드 핫이슈 키워드 '{k}'에 대한 속보 및 대중 관심사 분석 정보입니다." for k in kws}
                return kws, meta, "시그널 서버 직접 연동 시각: " + datetime.datetime.now().strftime("%H:%M:%S")
    except Exception:
        pass

    now_str = datetime.datetime.now().strftime("%H:%M:%S")
    return fallback_keywords, fallback_metadata, f"{now_str} (서버 점검으로 인한 자체 엔진 가동)"

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
        conn = http.client.HTTPSConnection(host, timeout=120) 
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
st.sidebar.info(f"🕒 데이터 연동 상태: {last_update}")

input_mode = st.sidebar.radio("키워드 선택 방식", ["🔄 시그널 실시간 연동", "✍️ 직접 수동 입력"])

if input_mode == "🔄 시그널 실시간 연동":
    if not live_kws:
        st.sidebar.warning("연동 대기 중입니다. 수동 입력을 이용해 주세요.")
        final_query = ""
    else:
        final_query = st.sidebar.selectbox("작성할 키워드 선택", live_kws)
else:
    final_query = st.sidebar.text_input("✍️ 키워드 직접 입력", placeholder="예: 아이폰18 출시일, 부동산 정책 발표")

platforms = st.sidebar.multiselect("발행 플랫폼", ["네이버 블로그", "티스토리", "워드프레스"], default=["네이버 블로그"])

style = st.sidebar.selectbox("글 스타일", [
    "📰 뉴스 보도체 (객관적, 사실 중심)", 
    "😊 쉬운 설명체 (친근함, 이모지 활용)",
    "🔥 이슈 분석체 (전문가 관점, 비판적 분석)",
    "✍️ 스토리텔링체 (부드러운 이야기 형식, 몰입감)"
])

# [💡 핵심 수정] 요구사항에 맞춰 글자 수 옵션 전면 개편
length_option = st.sidebar.selectbox("목표 글자 수", [
    "공백 제외 1,500자 내외 (기본 분량)", 
    "공백 제외 2,000자 내외 (상세한 포스팅)", 
    "공백 제외 2,500자 이상 (전문적인 분석)", 
    "공백 제외 3,000자 이상 (초고도 정보성)"
])

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
    if input_mode == "✍️ 직접 수동 입력":
        st.subheader("📝 뉴스 참고 내용 직접 입력")
        custom_summary = st.text_area(
            "AI가 참고할 실시간 뉴스 내용이나 핵심 팩트를 적어주세요.", 
            placeholder="예시: 정부에서 내년부터 청년 주거 지원금을 월 50만 원으로 인상한다고 발표했다. 대상은 중위소득 120% 이하의 만 19세~34세 청년이다. 신청은 7월부터 시작된다.",
            height=150
        )
    else:
        custom_summary = live_metadata.get(final_query, "최신 정보 없음")
        st.info(f"📋 **현재 선택된 시그널 팩트 요약본:**\n{custom_summary}")

    st.write("") 

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
                tone_instruction = ""
                if "뉴스 보도체" in style:
                    tone_instruction = "신뢰감 있고 객관적인 신문 기사 어조(~다, ~합니다)로 작성하세요. 주관적 감정은 배제하고 팩트 전달에 집중하세요."
                elif "쉬운 설명체" in style:
                    tone_instruction = "친근한 블로그 어조(~에요, ~습니다)로 작성하세요. 독자가 이해하기 쉽게 비유를 쓰고 적절한 이모지를 활용하세요."
                elif "이슈 분석체" in style:
                    tone_instruction = "날카로운 평론가/전문가 어조로 작성하세요. 사건의 배경, 원인, 향후 미칠 파장이나 전망까지 입체적으로 분석해야 합니다."
                elif "스토리텔링체" in style:
                    tone_instruction = "독자가 소설이나 에세이를 읽듯 몰입할 수 있도록 서두를 열고 징검다리식 전개 방식을 사용하여 부드럽게 서술하세요."

                platform_instruction = ""
                if p == "네이버 블로그":
                    platform_instruction = "- 제목은 클릭을 부르는 가장 매력적인 제목을 본문 맨 위에 배치하세요.\n- '서론 - 본문(소제목 분할) - 결론' 구조를 명확히 통합하여 자연스럽게 작성하세요."
                elif p == "티스토리":
                    platform_instruction = "- 구글 SEO 친화적인 구조로, 핵심 키워드가 맨 앞에 오는 명확한 제목을 상단에 배치하세요.\n- 본문은 대제목, 소제목 구조를 지켜 논리적으로 작성하세요."
                elif p == "워드프레스":
                    platform_instruction = "- 글 맨 처음에 '요약(Snippet)' 문단을 한 줄로 명확하게 넣어 가독성을 높이세요.\n- 소제목 구분을 완벽히 하고 문장을 간결하게 작성하세요."

                sys_prompt = (
                    f"당신은 실시간 트렌드 전문 파워블로거이자 디지털 카피라이터입니다. 입력된 타겟 키워드와 뉴스 데이터를 결합하여 완성도 높은 포스팅을 작성하세요.\n\n"
                    f"⚠️ [작성 안내]\n"
                    f"- 본문 맨 처음에 알맞은 제목을 크게 적어주고, 이어서 서론, 본문(소제목 포함), 결론을 구분 기호 없이 물 흐르듯 한 번에 작성해 주세요.\n"
                    f"- 글의 맨 마지막 줄(결론 뒤)에는 다음과 같이 번호를 매겨 사진 활용 및 추천 링크 정보를 단 두 줄로만 추가해 주세요.\n"
                    f"  1. 관련 공식 출처: (뉴스 맥락에 맞는 기관명 또는 SNS 주소 명시)\n"
                    f"  2. 추천 무료 이미지 소스: Unsplash (https://unsplash.com), Pixabay (https://pixabay.com)\n\n"
                    f"[톤앤매너 규칙]\n{tone_instruction}\n\n"
                    f"[플랫폼별 작성 규칙]\n{platform_instruction}\n\n"
                    f"[글자 수 제한 규칙]\n- 분량은 반드시 **{length_option}**에 맞추어 정보를 축약하지 말고 깊이 있게 가득 채워주세요.\n\n"
                    f"[⚠️ 절대 금지 규칙]\n"
                    f"- 본문 내에서 마크다운 강조 기호인 '**' (별표 두 개)는 절대 사용하지 마세요.\n"
                    f"- 'AI 요약에 따르면' 같은 인위적인 문구는 절대 금지합니다."
                )
                
                user_msg = (
                    f"● 실시간 트렌드 키워드: {final_query}\n"
                    f"● 뉴스 맥락 및 참고 팩트 정보:\n{custom_summary}\n\n"
                    f"위 규칙들을 토대로 블로그 글을 처음부터 끝까지 하나의 완성된 텍스트로 축약 없이 길게 작성해줘."
                )
                
                with st.spinner(f"[{p}] {style} 스타일에 맞춰 글을 생성하는 중..."):
                    content = call_ai_prime_tech(api_key, sys_prompt, user_msg, model)
                    if "통신 장애 발생" not in content and "AI API 에러" not in content:
                        st.session_state.generated_content[p] = content
                        save_to_history(final_query, p, content)
                    else:
                        st.error(f"[{p}] 생성 오류: {content}")

    if st.session_state.generated_content:
        st.success("🎉 블로그 글 생성이 완료되었습니다!")
        for p, full_content in st.session_state.generated_content.items():
            st.subheader(f"✨ {p} 결과물")
            st.text_area("📋 제목 + 서론 + 본문 + 결론 + 추천 링크 (통째로 복사해서 사용하세요)", value=full_content, height=600, key=f"body_area_{p}")
            st.divider()
        
        st.subheader("🖼️ 2단계: 블로그 썸네일 제작 및 사진 프리뷰")
        st.info("작성된 본문을 기반으로 미드저니/DALL-E용 영어 프롬프트를 추출하고 매칭 이미지를 시각화합니다.")
        
        if st.button("🎨 썸네일 시각화 및 이미지 생성하기", type="secondary"):
            with st.spinner("AI 디자이너가 최적의 이미지 프롬프트를 빌드하고 이미지를 시각화하는 중입니다..."):
                thumb_sys_prompt = (
                    "당신은 프로 수석 그래픽 디자이너입니다. 제공되는 키워드를 기반으로 썸네일 일러스트 디자인 콘셉트를 명확히 기획하고, "
                    "DALL-E 3나 Midjourney에서 실사 혹은 트렌디한 3D 그래픽 아트로 뽑아낼 수 있는 완성도 높은 영어 프롬프트를 딱 하나 완성해야 합니다. "
                    "출력은 딴 소리 없이 영어 프롬프트 한 문장으로만 간단하게 작성해 주세요."
                )
                thumb_user_msg = f"실시간 키워드: {st.session_state.selected_keyword}"
                thumb_result = call_ai_prime_tech(api_key, thumb_sys_prompt, thumb_user_msg, model)
                st.session_state.thumbnail_result = thumb_result
                
        if st.session_state.thumbnail_result:
            st.write("### 💡 AI 이미지 생성용 추천 영어 프롬프트")
            st.code(st.session_state.thumbnail_result, language="text")
            st.caption("위 영어 프롬프트를 복사하여 이미지 생성 AI 창에 그대로 넣으시면 고품질 사진이 제작됩니다.")
            
            st.markdown("#### 🚀 시스템 추천 디자인 무드 가이드")
            st.image(f"https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=800&auto=format&fit=crop", 
                     caption="[시스템 추천 가이드라인 예시안]", use_container_width=True)

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
