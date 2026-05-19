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

# 세션 상태 초기화 (API Key 보관 유지)
if "api_key_storage" not in st.session_state:
    st.session_state.api_key_storage = ""
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
        
        if "content" in result_json:
            content_data = result_json["content"]
            if isinstance(content_data, list) and len(content_data) > 0:
                if isinstance(content_data[0], dict) and "text" in content_data[0]:
                    return content_data[0]["text"]
                elif isinstance(content_data[0], str):
                    return content_data[0]
            elif isinstance(content_data, str):
                return content_data
        
        if "choices" in result_json and len(result_json["choices"]) > 0:
            choice = result_json["choices"][0]
            if "message" in choice and "content" in choice["message"]:
                return choice["message"]["content"]
            elif "text" in choice:
                return choice["text"]
                
        if "text" in result_json:
            return result_json["text"]
            
        if "error" in result_json:
            return f"AI API 에러 발생: {result_json['error']}"
            
        if data.strip():
            return f"⚠️ [안내: 규격 외 응답 수신] 데이터 원본을 출력합니다:\n\n{data}"
            
        return "본문 텍스트가 비어있습니다. (서버가 빈 값을 반환함)"
        
    except Exception as e:
        return f"통신 장애 발생: {str(e)}"

# 3. 화면 UI 및 사이드바 설정
st.title("📰 실시간 이슈 뉴스 블로그 글 생성기")

st.sidebar.header("🔑 설정 및 시그널")

# API 키 세션 유지 상자
api_key = st.sidebar.text_input(
    "AI Prime Tech API Key", 
    value=st.session_state.api_key_storage, 
    type="password"
)
if api_key != st.session_state.api_key_storage:
    st.session_state.api_key_storage = api_key

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

# [🔥 핵심 수정: 글자 수 범위를 명확한 '최소 제한선' 기준으로 세분화 변경]
length_option = st.sidebar.selectbox("목표 글자 수 (최소 보장 기준)", [
    "공백 제외 최소 1,500자 이상 (일반 포스팅용)", 
    "공백 제외 최소 2,000자 이상 (상세 고품질용)", 
    "공백 제외 최소 2,500자 이상 (전문 분석용)", 
    "공백 제외 최소 3,000자 이상 (초고도 정보성)"
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

    # 글 생성하기 버튼
    if st.button("🚀 블로그 글 생성하기", type="primary"):
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
            
            # 실제 프롬프트에 주입할 글자 수 텍스트만 추출
            target_length = length_option.split("(")[0].strip()

            for p in platforms:
                tone_instruction = ""
                if "뉴스 보도체" in style:
                    tone_instruction = "신뢰감 있고 객관적인 신문 기사 어조 (~다, ~합니다)로 작성하세요. 주관적 감정은 배제하고 팩트 전달에 집중하세요."
                elif "쉬운 설명체" in style:
                    tone_instruction = "친근한 블로그 어조 (~에요, ~습니다)로 작성하세요. 독자가 이해하기 쉽게 비유를 쓰고 적절한 이모지를 활용하세요."
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
                    f"당신은 네이버의 스마트블록(C-Rank, DIA+) 알고리즘을 꿰뚫고 있는 실시간 트렌드 전문 파워블로거입니다. "
                    f"입력된 키워드와 뉴스 데이터를 분석하여 완벽한 상위 노출용 포스팅을 작성하세요.\n\n"
                    f"⚠️ [작성 안내]\n"
                    f"- 본문 맨 처음에 알맞은 제목을 크게 적어주고, 이어서 서론, 본문(소제목 포함), 결론을 구분 기호 없이 한 번에 작성해 주세요.\n"
                    f"- 이미지나 외부 링크 추천 관련 멘트는 절대로 적지 마세요.\n\n"
                    f"🔢 [🔥 글자 수 절대 준수 규칙 - 최우선 체크]\n"
                    f"- 작성되는 순수 본문(태그 제외)의 분량은 무조건 **{target_length}**을 넘겨야 합니다.\n"
                    f"- 대충 요약해서 분량이 미달되면 안 됩니다. 정보가 부족하다면 팩트의 배경, 사회적 파장, 네티즌들의 반응, 향후 전망, 주의사항 등의 소제목을 추가로 개설해서라도 문장을 길고 구체적으로 늘려 쓰세요.\n\n"
                    f"🏷️ [스마트블록 최적화 태그 생성 규칙]\n"
                    f"- 결론이 끝난 뒤 맨 마지막 줄에, 네이버 스마트블록 세부 분류에 노출되기 적합한 **연관 핵심 태그를 반드시 20개 이상** 한 줄로 이어서 작성하세요.\n"
                    f"- 태그는 대중의 검색 의도, 파생 키워드, 타겟층이 골고루 조합된 고품질 키워드로 구성해야 합니다.\n"
                    f"- 출력 형식 예시: #키워드1 #키워드2 #세부키워드3 ... (20개 이상 채울 것)\n\n"
                    f"[톤앤매너 규칙]\n{tone_instruction}\n\n"
                    f"[플랫폼별 작성 규칙]\n{platform_instruction}\n\n"
                    f"[⚠️ 절대 금지 규칙]\n"
                    f"- 본문 내에서 마크다운 강조 기호인 '**' (별표 두 개)는 절대 사용하지 마세요.\n"
                    f"- 'AI 요약에 따르면' 같은 인위적인 문구는 절대 금지합니다."
                )
                
                user_msg = (
                    f"● 실시간 트렌드 키워드: {final_query}\n"
                    f"● 뉴스 맥락 및 참고 팩트 정보:\n{custom_summary}\n\n"
                    f"위 규칙들을 토대로 블로그 글을 작성하고, 본문 분량 규칙인 '{target_length}'을 절대적으로 지켜서 길게 써줘. 마지막 줄에 스마트블록 태그 20개 이상도 빼놓지 마."
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
            st.text_area("📋 제목 + 본문 + 스마트블록 최적화 태그 20개+ (통째로 복사해서 사용하세요)", value=full_content, height=650, key=f"body_area_{p}")
            st.divider()

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
