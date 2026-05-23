import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from datetime import datetime

# ==========================================
# ⚙️ 네이버 연예/방송 뉴스 URL 설정
# ==========================================
NAVER_ENT_URL = "https://news.naver.com/section/106" 

def fetch_naver_entertainment_news():
    """네이버 연예 뉴스 최신 헤드라인을 가져옵니다."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(NAVER_ENT_URL, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        
        articles = []
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
        
        return pd.DataFrame(articles).drop_duplicates(subset=["title"]).head(15)
    except Exception as e:
        st.error(f"네이버 뉴스 연결 실패: {e}")
        return pd.DataFrame(columns=["title", "url", "time"])

# ==========================================
# 🖥️ Streamlit 대시보드 UI 설정
# ==========================================
st.set_page_config(page_title="실시간 뉴스 사운드 레이더", page_icon="🔔", layout="wide")

st.title("🔔 웹 전용 실시간 뉴스 사운드 레이더")
st.caption(f"현재 스캔 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 외부 앱 연동 없이 이 화면에서 바로 알림")

# 브라우저 소리 재생을 위한 알림음 링크 (저작권 프리 알림음)
BEEP_SOUND_URL = "https://actions.google.com/sounds/v1/alarms/digital_watch_alarm_long.ogg"

# 세션 상태(메모리) 초기화
if "processed_news" not in st.session_state:
    st.session_state.processed_news = set()
if "alert_triggered" not in st.session_state:
    st.session_state.alert_triggered = False
if "new_arrival_list" not in st.session_state:
    st.session_state.new_arrival_list = []

# 크롤링 엔진 가동
df = fetch_naver_entertainment_news()

if not df.empty:
    current_titles = set(df["title"].tolist())
    
    # [최초 가동 시] 현재 떠 있는 뉴스들은 알림 대상에서 제외 (베이스라인 설정)
    if not st.session_state.processed_news:
        st.session_state.processed_news = current_titles
        st.info("🎯 뉴스 모니터링 사이트가 활성화되었습니다. 1분 뒤 새로운 뉴스가 들어오면 이 화면에서 소리와 함께 즉시 경보가 울립니다!")
    else:
        # 1분 전 데이터와 대조하여 완전히 새로운 기사만 추출
        new_articles_df = df[~df["title"].isin(st.session_state.processed_news)]
        
        if not new_articles_df.empty:
            # 신규 기사 목록을 세션에 업데이트
            st.session_state.new_arrival_list = new_articles_df.to_dict('records')
            # 다음 턴 비교를 위해 기록 저장
            st.session_state.processed_news.update(new_articles_df["title"].tolist())
            # 알림 플래그 켜기
            st.session_state.alert_triggered = True
        else:
            # 새로운 기사가 안 올라왔다면 플래그 끄기
            st.session_state.alert_triggered = False

    # ==========================================
    # 🔊 🚨 신규 뉴스 발생 시 브라우저 알림 (소리 + 시각 효과)
    # ==========================================
    if st.session_state.alert_triggered and st.session_state.new_arrival_list:
        # 1. 딩동 소리 재생 (HTML5 Audio 태그를 활용해 브라우저에서 소리 강제 재생)
        st.markdown(f'<audio autoplay><source src="{BEEP_SOUND_URL}" type="audio/ogg"></audio>', unsafe_allow_html=True)
        
        # 2. 최상단 사이트 경보 팝업 시각화
        st.subheader("🔥 레이더 포착: 실시간 신규 기사 발생!")
        for row in st.session_state.new_arrival_list:
            st.markdown(f"""
                <div style="background-color: #fff0f6; border: 2px solid #ff4d4f; border-left: 8px solid #ff4d4f; border-radius: 8px; padding: 18px; margin-bottom: 15px; animation: pulse 1.5s infinite;">
                    <span style="font-weight: bold; color: #ff4d4f; font-size: 1rem;">🚨 [실시간 기사 등록 완료 / 사이트 사운드 경보 발령]</span>
                    <span style="color: #8c8c8c; font-size: 0.85rem; margin-left: 10px;">({row['time']})</span><br style="margin-bottom: 8px;">
                    <a href="{row['url']}" target="_blank" style="text-decoration: none; color: #141414; font-size: 1.2rem; font-weight: bold; hover: text-decoration: underline;">{row['title']}</a>
                </div>
            """, unsafe_allow_html=True)
        st.markdown("---")

    # 3. 전체 실시간 뉴스 타임라인 스트림
    st.subheader("📋 전체 실시간 연예/방송 뉴스 스트림 (최신순)")
    
    # 가독성을 높이기 위해 깔끔한 마크다운 리스트 형태로 배치
    for idx, row in df.iterrows():
        st.markdown(f"⏱️ `{row['time']}` | [{row['title']}]({row['url']})")

else:
    st.warning("네이버 뉴스 데이터를 받아오지 못했습니다. 1분 후 새로고침합니다.")

# ==========================================
# ⏳ 1분(60초) 뒤 정확히 브라우저 새로고침
# ==========================================
time.sleep(60)
st.rerun()
