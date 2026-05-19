import streamlit as st
import requests
import json
import anthropic # 형이 기존에 사용하던 Claude 라이브러리 (맞지?)

# 1. 데이터 가져오기 (JSONBin)
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

# 2. Claude AI 글쓰기 함수
def generate_blog_post(keyword, summary):
    # 여기에 형이 발급받은 API 키를 넣어주거나 환경변수를 사용해야 해
    client = anthropic.Anthropic(api_key="형의_API_KEY_여기에") 
    
    prompt = f"""
    당신은 인기 블로거입니다. 아래 [팩트 정보]를 바탕으로 글을 작성하세요.
    [팩트 정보]
    키워드: {keyword}
    내용: {summary}
    [작성 규칙]
    1. 외부 검색을 절대 하지 마세요. 제공된 [팩트 정보]만 활용하세요.
    2. 클릭을 유도하는 매력적인 제목과 내용을 작성하세요.
    """
    
    message = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text

# 3. 메인 화면
st.title("블로그 자동 글쓰기 도우미")

keywords, metadata, updated_at = load_extension_data()
st.write(f"최근 동기화: {updated_at}")

selected_keyword = st.selectbox("글 쓸 키워드를 선택하세요:", keywords)

if st.button("글 생성하기"):
    if selected_keyword:
        summary = metadata.get(selected_keyword, "별도의 요약 정보가 없습니다.")
        st.write("### 팩트 체크:")
        st.info(summary)
        
        with st.spinner("AI가 글을 작성 중입니다..."):
            try:
                result = generate_blog_post(selected_keyword, summary)
                st.success("글 작성이 완료되었습니다!")
                st.text_area("결과물:", value=result, height=400)
            except Exception as e:
                st.error(f"글 생성 실패: {str(e)}")
    else:
        st.error("데이터를 불러오지 못했습니다. 확장 프로그램을 확인해주세요!")
