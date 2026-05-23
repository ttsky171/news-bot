import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from datetime import datetime

# ==========================================
# ⚙️ 사용자 설정 (실제 값으로 꼭 변경하세요)
# ==========================================
TELEGRAM_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
CHAT_ID = "YOUR_TELEGRAM_CHAT_ID"

# 네이버 연예/방송 뉴스 URL
NAVER_ENT_URL = "https://news.naver.com/section/106" 

# ==========================================
# 📩 무조건 푸시 알림 발송 함수
# ==========================================
def send_push_notification(title, url):
    """새로운 기사가 발견되면 조건 없이 즉시 텔레그램 푸시를 발송합니다."""
    message = f"📢 [신규 연예 뉴스 등록!]\n\n제목: {title}\n링크: {url}"
    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(telegram_url, json=payload, timeout=5)
    except Exception as e:
        print(f"텔레그램 푸시 발송 실패: {e}")

def fetch_naver_entertainment_news():
    """네이버 연예 뉴스 최신 헤드라인을 가져옵니다."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(NAVER_ENT_URL, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        
        articles = []
        # 네이버 뉴스 다중 선택자 매칭
        titles = soup.select(".sa_text_title") or soup.select(".sa_text a") or soup.select(".newsct_text_title")
        
        for item in titles:
            title_text = item.get_text().strip()
            link = item.get("href")
            if title_text and link:
                articles.append({
                    "title": title_text, 
                    "url": link, 
                    "time": datetime.now().strftime("%H:%M:%S")
                })
        
        # 중복 기사 제거 후 최신 15개 반환
        return pd.DataFrame(articles).drop_duplicates(subset=["title"]).head(15)
    except Exception as e:
        st.error(f"데이터 크롤링 실패 (네이버 서버 응답 없음): {e}")
        return pd.DataFrame(columns=["title", "url", "time"])

# ==========================================
# 🖥️ Streamlit 대시보드 UI
# ==========================================
st.set_page_config(page_title="실시간 뉴스 올패스 알림", page_icon="🚨", layout="wide")

st.title("🚨 실시간 연예 뉴스 올패스(All-Pass) 레이더")
st.caption(f"현재 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 1분마다 신규 기사 전수 검사 중")

st.sidebar.header("📡 레이더 가동 상태")
st.sidebar.success("정상 작동 중: 연예 탭의 모든 신규 뉴스 감시 중")
st.sidebar.warning("⚠️ 주의: 연예 뉴스는 등록 빈도가 매우 높아 폰 알림이 자주 울릴 수 있습니다.")

# 기사 히스토리 관리를 위한 세션 초기화
if "processed_news" not in st.session_state:
    st.session_state.processed_news = set()
if "last_new_articles" not in st.session_state:
    st.session_state.last_new_articles = []

# 크롤링 엔진 가동
df = fetch_naver_entertainment_news()

if not df.empty:
    current_titles = set(df["title"].tolist())
    
    # 처음 실행한 순간에는 현재 떠 있는 기사들을 기본 베이스라인으로 등록합니다.
    # (프로그램을 켜자마자 기존 기사 15개가 한 번에 폰으로 쏟아지는 것을 방지)
    if not st.session_state.processed_news:
        st.session_state.processed_news = current_titles
        new_articles_df = pd.DataFrame(columns=["title", "url", "time"])
        st.info("⚡ 실시간 뉴스 레이더를 구축했습니다. 지금 이 순간 이후로 올라오는 모든 뉴스부터 즉시 푸시 알림이 발송됩니다.")
    else:
        # 1. 1분 전 스캔 결과와 대조하여 완전히 새로운 기사만 추출
        new_articles_df = df[~df["title"].isin(st.session_state.processed_news)]
        # 신규 기사들을 히스토리에 누적 업데이트
        st.session_state.processed_news.update(new_articles_df["title"].tolist())

    # 새로운 기사가 발견되었다면 화면 상단 갱신용 세션에 저장
    if not new_articles_df.empty:
        st.session_state.last_new_articles = new_articles_df.to_dict('records')

    # 2. 대시보드 상단 강조 영역 (방금 폰으로 날아간 기사들)
    if st.session_state.last_new_articles:
        st.subheader("🔥 방금 스마트폰으로 발송된 신규 뉴스")
        for row in st.session_state.last_new_articles:
            st.markdown(f"""
                <div style="background-color: #fffbe6; border-left: 6px solid #faad14; border-radius: 6px; padding: 16px; margin-bottom: 12px;">
                    <span style="font-weight: bold; color: #d46b08; font-size: 0.9rem;">⚡ [실시간 푸시 완료]</span>
                    <span style="color: #8c8c8c; font-size: 0.8rem; margin-left: 8px;">({row['time']})</span><br>
                    <a href="{row['url']}" target="_blank" style="text-decoration: none; color: #1f1f1f; font-size: 1.15rem; font-weight: bold;">{row['title']}</a>
                </div>
            """, unsafe_allow_html=True)
            
            # 중복 전송을 막기 위해 이번에 새로 긁어온 데이터프레임에 존재할 때만 딱 한 번 푸시 발송
            if not new_articles_df.empty and row["title"] in new_articles_df["title"].values:
                send_push_notification(row["title"], row["url"])
        st.markdown("---")

    # 3. 네이버 뉴스 실시간 전체 스트림
    st.subheader("📋 현재 네이버 뉴스 홈 스트림 (최신순)")
    for idx, row in df.iterrows():
        st.markdown(f"⏱️ `{row['time']}` | [{row['title']}]({row['url']})")

else:
    st.warning("네이버 뉴스 데이터를 가져오지 못했습니다. 1분 후 다시 연결을 시도합니다.")

# ==========================================
# ⏳ 1분(60초) 주기 자동 새로고침 무한 루프
# ==========================================
time.sleep(60)
st.rerun()
