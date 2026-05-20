import streamlit as st
import json
import http.client
import os
import datetime
import glob
import urllib.request
import re

# 페이지 설정
st.set_page_config(page_title="실시간 뉴스 블로그 생성기 Pro", page_icon="📰", layout="wide")

# 폴더 관리
HISTORY_DIR = "blog_history"
CONFIG_DIR = "blog_config"
for folder in [HISTORY_DIR, CONFIG_DIR]:
    if not os.path.exists(folder): 
        os.makedirs(folder)

# API 키 파일 저장/로드 함수
KEY_FILE = os.path.join(CONFIG_DIR, "api_key.txt")

def load_saved_api_key():
    if os.path.exists(KEY_FILE):
        try:
            with open(KEY_FILE, "r", encoding="utf-8") as f:
                return f.read().strip()
        except:
            return ""
    return ""

def save_api_key(key):
    try:
        with open(KEY_FILE, "w", encoding="utf-8") as f:
            f.write(key.strip())
    except:
        pass

if "api_key_storage" not in st.session_state:
    st.session_state.api_key_storage = load_saved_api_key()
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

# 외국어 및 한자 오염 방지 화이트리스트 필터 함수
def clean_foreign_languages(text):
    if not text:
        return text
    # 한글(가-힣), 영문(a-zA-Z), 숫자(0-9), 해시태그(#), 줄바꿈(\n), 공백(\s), 기본 문장부호만 허용
    allowed_pattern = re.compile(r'[^가-힣a-zA-Z0-9#\s\n.,?!~\"\'\(\)\[\]\-\_\·\’\‘\“\”\…]')
    cleaned_text = allowed_pattern.sub('', text)
    cleaned_text = re.sub(r' +', ' ', cleaned_text)
    return cleaned_text

# 1. JSONBin 및 시그널 데이터 로드
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

# 2. AI 호출 엔진 (전달받은 복합 데이터 완벽 파싱 버전)
def call_ai_prime_tech(key, sys_prompt, user_msg, model_name):
    host = "aiprimetech.io"
    payload = json.dumps({
        "model": model_name,
        "max_tokens": 4000, 
        "messages": [{"role": "user", "content": f"[System 규칙: {sys_prompt}]\n\n{user_msg}"}]
    })
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {key}'}
    
    try:
        conn = http.client.HTTPSConnection(host, timeout=240) 
        conn.request("POST", "/v1/messages", payload, headers)
        res = conn.getresponse()
        data = res.read().decode("utf-8")
        conn.close()
        
        if not data or data.strip() == "":
            return "API 서버로부터 아무런 데이터도 응답받지 못했습니다. (빈 응답)"

        try:
            result_json = json.loads(data)
        except Exception:
            return f"JSON 파싱 실패. 서버 원본 메시지:\n{data}"
        
        raw_text = ""
        
        # 🎯 [핵심] content 배열 내부에 thinking과 text가 나뉘어 들어오는 구조를 완벽하게 파싱
        if "content" in result_json and isinstance(result_json["content"], list):
            text_pieces = []
            for item in result_json["content"]:
                if isinstance(item, dict):
                    # type이 text인 진짜 본문만 수집
                    if item.get("type") == "text" and "text" in item:
                        text_pieces.append(item["text"])
                    # 혹시 모를 예외 구조 대비
                    elif "text" in item and item.get("type") != "thinking":
                        text_pieces.append(item["text"])
            
            if text_pieces:
                raw_text = "".join(text_pieces)
        
        # [백업 구조 1] content가 일반 문자열로 들어오는 경우
        if not raw_text and "content" in result_json and isinstance(result_json["content"], str):
            raw_text = result_json["content"]
        
        # [백업 구조 2] OpenAI 스타일 규격 (choices)으로 들어오는 경우
        if not raw_text and "choices" in result_json and len(result_json["choices"]) > 0:
            choice = result_json["choices"][0]
            if "message" in choice and "content" in choice["message"]:
                raw_text = choice["message"]["content"]
            elif "text" in choice:
                raw_text = choice["text"]
                
        # [백업 구조 3] 루트 레벨에 바로 text가 포함되어 오는 경우
        if not raw_text and "text" in result_json:
            raw_text = result_json["text"]
            
        # 에러 블록 처리
        if "error" in result_json:
            return f"AI API 내부 에러 발생: {result_json['error']}"
        
        # 최종 본문 텍스트 청소 및 다듬기
        if raw_text and raw_text.strip() != "":
            # 1차 허용 문자 필터링
            cleaned = clean_foreign_languages(raw_text)
            
            # 2차: 문장 내부에 강제로 끼어든 알파벳 찌꺼기 단어 완전 제거 (예: 고confortable 했던 -> 했던)
            cleaned = re.sub(r'[a-zA-Z가-힣]*[a-zA-Z\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff]+[a-zA-Z가-힣]*', '', cleaned)
            cleaned = re.sub(r' +', ' ', cleaned)  # 중복 공백 청소
            
            return cleaned.strip()
            
        return f"본문 텍스트 추출 실패. 서버 수신 응답 데이터 원본:\n{json.dumps(result_json, ensure_ascii=False, indent=2)}"
        
    except Exception as e:
        return f"통신 장애 발생: {str(e)}"

# 3. 화면 UI 및 사이드바 설정
st.title("📰 실시간 이슈 뉴스 블로그 글 생성기")

st.sidebar.header("🔑 설정 및 시그널")

api_key = st.sidebar.text_input(
    "AI Prime Tech API Key", 
    value=st.session_state.api_key_storage, 
    type="password"
)

if api_key != st.session_state.api_key_storage:
    st.session_state.api_key_storage = api_key
    save_api_key(api_key)

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
    final_query = st.sidebar.text_input("✍️ 키워드 직접 입력", placeholder="예: 아이폰18 출시일")

platforms = st.sidebar.multiselect("발행 플랫폼", ["네이버 블로그", "티스토리", "워드프레스"], default=["네이버 블로그"])

style = st.sidebar.selectbox("글 스타일", [
    "📰 뉴스 보도체 (객관적, 사실 중심)", 
    "😊 쉬운 설명체 (친근함, 이모지 활용)",
    "🔥 이슈 분석체 (전문가 관점, 비판적 분석)",
    "✍️ 스토리텔링체 (부드러운 이야기 형식)"
])

length_option = st.sidebar.selectbox("목표 글자 수 (최소 보장 기준)", [
    "공백 제외 최소 1,500자 이상", 
    "공백 제외 최소 2,000자 이상", 
    "공백 제외 최소 2,500자 이상"
])

st.sidebar.divider()

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
            height=150
        )
    else:
        custom_summary = live_metadata.get(final_query, "최신 정보 없음")
        st.info(f"📋 **현재 선택된 시그널 팩트 요약본:**\n{custom_summary}")

    st.write("") 

    if st.button("🚀 블로그 글 생성하기", type="primary"):
        if not api_key:
            st.error("API 키를 입력하세요.")
        elif not final_query or final_query.strip() == "":
            st.error("작성할 키워드를 선택하거나 직접 입력해 주세요.")
        elif not platforms:
            st.warning("발행 플랫폼을 최소 하나 이상 선택해주세요.")
        else:
            st.session_state.selected_keyword = final_query
            st.session_state.generated_content = {} 
            
            target_length = length_option.split(" ")[3] + "자 이상"

            for p in platforms:
                tone_instruction = ""
                if "뉴스 보도체" in style:
                    tone_instruction = "신뢰감 있고 객관적인 신문 기사 어조 (~다, ~합니다)로 작성하세요."
                elif "쉬운 설명체" in style:
                    tone_instruction = "친근한 블로그 어조 (~에요, ~습니다)로 작성하고 알맞은 이모지를 섞으세요."
                elif "이슈 분석체" in style:
                    tone_instruction = "날카로운 전문 평론가 입장에서 깊이 있는 배경 분석과 전망을 서술하세요."
                elif "스토리텔링체" in style:
                    tone_instruction = "독자가 읽기 편안하도록 부드러운 호흡의 이야기 형식으로 서술하세요."

                platform_instruction = ""
                if p == "네이버 블로그":
                    platform_instruction = "- 제목은 맨 위에 한 줄로 적고 바로 서론으로 자연스럽게 진입하세요.\n- 단락 사이에는 엔터를 2번 쳐서 가독성을 확보하세요."
                elif p == "티스토리":
                    platform_instruction = "- 핵심 키워드가 잘 드러나는 제목을 상단에 깔끔하게 배치하세요."
                elif p == "워드프레스":
                    platform_instruction = "- 문장을 간결하고 깔끔하게 마침표로 딱 끊어지도록 마무리지으세요."

                sys_prompt = (
                    f"당신은 검색 알고리즘 최적화를 완벽히 마스터한 블로그 포스팅 전문가입니다. "
                    f"입력된 키워드와 뉴스를 바탕으로 한국인 독자가 가독성 높게 읽을 수 있는 매끄러운 글을 작성하세요.\n\n"
                    f"🛑 [외국어 어휘 및 일어/중국어/한자 전면 사용 금지 지침]\n"
                    f"- 문맥 도중에 한자, 일본어 단어, 조사, 중국어 번역투가 절대로 섞여 나오지 않도록 각별히 유의하세요.\n"
                    f"- 모든 문장은 반드시 올바른 문법의 순수 '한국어' 표준 문장으로만 완성되어야 합니다.\n\n"
                    f"❌ [마크다운 문법 및 강조 기호 사용 전면 금지]\n"
                    f"- 본문 어느 곳에도 '**', '###', '##', '*', '-', '◆', '■' 같은 마크다운 기호 및 특수문자를 절대 쓰지 마세요.\n"
                    f"- 문단을 구분하는 소제목은 아무런 기호 없이 평범한 텍스트나 숫자 넘버링 형태로만 적고, 줄바꿈을 넉넉히 하세요.\n\n"
                    f"🔢 [글자 수 규칙]\n"
                    f"- 작성되는 순수 본문 분량은 무조건 {target_length} 이상이어야 합니다. 내용을 다양하고 구체적인 문장들로 채워 넣으세요.\n\n"
                    f"🏷️ [최적화 태그 생성 규칙]\n"
                    f"- 글 맨 마지막 단락에 블로그용 해시태그를 공백과 '#' 기호로만 조합하여 20개 이상 나열해 주세요.\n\n"
                    f"[톤앤매너 규칙]\n{tone_instruction}\n\n"
                    f"[플랫폼별 작성 규칙]\n{platform_instruction}"
                )
                
                user_msg = (
                    f"● 키워드: {final_query}\n"
                    f"● 뉴스 맥락 정보:\n{custom_summary}\n\n"
                    f"위 지침을 토대로 글을 작성해줘. 절대로 문장 중간에 불필요한 한자나 중국어, 일본어 문법 찌꺼기가 섞여 나오지 않도록 텍스트 품질을 엄격하게 관리해줘."
                )
                
                with st.spinner(f"[{p}] 글을 생성하고 유효성을 점검하는 중..."):
                    content = call_ai_prime_tech(api_key, sys_prompt, user_msg, model)
                    st.session_state.generated_content[p] = content
                    
                    if "추출 실패" not in content and "에러 발생" not in content and "통신 장애" not in content:
                        save_to_history(final_query, p, content)

    if st.session_state.generated_content:
        for p, full_content in st.session_state.generated_content.items():
            st.subheader(f"✨ {p} 결과 안내")
            st.text_area("📋 출력 창", value=full_content, height=650, key=f"body_area_{p}")
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
