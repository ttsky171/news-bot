import streamlit as st
import requests
import json

# 1. 설정 및 데이터 가져오기 (JSONBin)
def load_extension_data():
    BIN_ID = "6a0c24886610dd3ae86c19cd"
    MASTER_KEY = "$2a$10$XJlSzhQ1AoOvMQqIH95KOeLDbr7ohp4ocKXh2V3iAJxHW.QvAnOm6"
    url = f"https://api.jsonbin.io/v3/b/{BIN_ID}/latest"
    headers = {"X-Master-Key": MASTER_KEY}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            res_data = response.json().get("record", {})
            return (
                res_data.get("keywords", []), 
                res_data.get("metadata", {}), 
                res_data.get("updated_at", "동기화 시간 없음")
            )
        return [], {}, "연결 오류"
    except:
        return [], {}, "통신 실패"

# 2. AI 글쓰기 함수 (Claude 연동)
def generate_blog_post(keyword, summary):
    # 여기서 형이 쓰는 AI API 호출 방식이 들어감
    # 지금 받은 에러 메시지를 보면 Claude API를 쓰는 것 같아서 그 구조로 작성함
    
    prompt = f"""
    당신은 인기 블로거입니다. 아래 [팩트 정보]를 바탕으로 사람들의 클릭을 유도하는 매력적인 블로그 글을 작성하세요.
    
    [팩트 정보]
    키워드: {keyword}
    내용: {summary}
    
    [작성 규칙]
    1. 외부 검색을 절대 하지 마세요. 제공된 [팩트 정보]만 활용하세요.
    2. 제목은 사람들의 호기심을 자극하는 문구로 만드세요.
    3. 읽기 쉬운 문체와 적절한 줄바꿈을 사용하세요.
    4. 정보가 부족하면 있는 내용만 정성스럽게 작성하세요.
    """
    
    # 실제 API 호출 로직은 형이 기존에 쓰던 부분을 여기에 넣으면 돼!
    # (일단은 형이 보여준 메시지가 뜨는 기존 함수를 그대로 유지하고, 위에 프롬프트만 잘 수정해봐)
    return f"AI가 작성한 글 결과물 (키워드: {keyword}, 요약: {summary})"

# 3. 화면 구성 (Streamlit)
st.title("블로그 자동 글쓰기 도우미")

keywords, metadata, updated_at = load_extension_data()
st.write(f"최근 동기화: {updated_at}")

selected_keyword = st.selectbox("글 쓸 키워드를 선택하세요:", keywords)

if st.button("글 생성하기"):
    if selected_keyword:
        summary = metadata.get(selected_keyword, "별도의 요약 정보가 없습니다.")
        st.write("### 선택한 키워드 요약:")
        st.info(summary)
        
        # 글 생성 실행
        with st.spinner("AI가 글을 작성 중입니다..."):
            result = generate_blog_post(selected_keyword, summary)
            st.success("글 작성이 완료되었습니다!")
            st.text_area("결과물:", value=result, height=400)
    else:
        st.error("키워드가 없습니다!")
