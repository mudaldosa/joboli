import streamlit as st
import requests
from bs4 import BeautifulSoup
from google.cloud import firestore
from google.oauth2 import service_account
import json
import random
from datetime import datetime
import urllib.parse
import pytz 
import time

# --- 1. 🎨 반응형 디자인 설정 ---
st.set_page_config(page_title="BBC News Quiz", page_icon="🌟", layout="wide")

st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background-color: #0E1117; color: white; }
    [data-testid="stSidebar"] { display: none; }
    h1, h2, h3, h4, p, span { color: white !important; font-family: 'Pretendard', sans-serif; }
    h1 { color: #FFD700 !important; text-align: center; font-weight: bold; margin-bottom: 20px; font-size: 1.8rem !important; }

    .main-wrapper { max-width: 700px; margin: 0 auto; padding: 10px; }

    .stTextInput > div > div > input {
        background-color: #1A1C23 !important;
        color: white !important;
        border: 2px solid #FFD700 !important;
        border-radius: 12px !important;
        padding: 12px 15px !important;
        font-size: 1.1rem !important;
    }

    .stButton > button {
        background-color: #FFD700 !important;
        color: #0E1117 !important;
        font-weight: bold !important;
        border-radius: 12px !important;
        width: 100% !important;
        height: 45px !important;
        font-size: 0.95rem !important;
        border: none !important;
        margin-top: 5px;
    }

    .ranking-container {
        background-color: #1A1C23; border: 2px solid #FFD700;
        border-radius: 15px; padding: 15px; margin-bottom: 20px;
    }
    .ranking-title { color: #FFD700 !important; font-weight: bold; text-align: center; border-bottom: 1px solid #444; margin-bottom: 10px; }
    .ranking-item { display: flex; justify-content: space-between; margin-bottom: 5px; font-size: 0.95rem; border-bottom: 1px dashed #333; padding-bottom: 3px; }

    .quiz-card { background-color: #262730; border-radius: 20px; padding: 25px; border: 1px solid #444; margin-bottom: 15px; }

    .wrong-x {
        position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
        font-size: 12rem; color: #FF6347; z-index: 10000; animation: fade-out 1s forwards; pointer-events: none;
    }
    @keyframes fade-out { 0% {opacity: 1; transform: translate(-50%, -50%) scale(1.2);} 100% {opacity: 0; transform: translate(-50%, -50%) scale(0.8);} }
</style>
""", unsafe_allow_html=True)

# --- 2. 🌍 시간 및 DB 설정 ---
KST = pytz.timezone('Asia/Seoul')
today = datetime.now(KST).strftime("%Y-%m-%d")

if "db" not in st.session_state:
    key_dict = json.loads(st.secrets["firebase"]["info"])
    creds = service_account.Credentials.from_service_account_info(key_dict)
    st.session_state.db = firestore.Client(credentials=creds)

db = st.session_state.db

# --- 3. 🏆 랭킹 로직 ---
def display_ranking():
    st.markdown('<div class="ranking-container"><div class="ranking-title">🏆 오늘의 TOP 5</div>', unsafe_allow_html=True)
    try:
        docs = db.collection("quiz_users").where("last_date", "==", today).limit(50).stream()
        data = [d.to_dict() | {"name": d.id} for d in docs]
        sorted_data = sorted(data, key=lambda x: x.get('score', 0), reverse=True)[:5]
        
        if not sorted_data:
            st.markdown('<div style="text-align:center; color:#888;">오늘의 첫 주인공이 되세요!</div>', unsafe_allow_html=True)
        else:
            medals = ["🥇", "🥈", "🥉", "4.", "5."]
            for i, user in enumerate(sorted_data):
                st.markdown(f'<div class="ranking-item"><span>{medals[i]} {user["name"]}</span><span><b>{user["score"]}점</b></span></div>', unsafe_allow_html=True)
    except:
        st.markdown('<div style="text-align:center;">데이터 로딩 중...</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# --- 4. 🧠 퀴즈 로직 ---
def translate_to_ko(text):
    try:
        url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=ko&dt=t&q=" + urllib.parse.quote(text)
        return requests.get(url).json()[0][0][0]
    except: return "번역 실패"

def get_bbc_quiz():
    try:
        url = "https://www.bbc.com/news"
        soup = BeautifulSoup(requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).text, 'html.parser')
        titles = [h.get_text().strip() for h in soup.find_all('h2') if 7 < len(h.get_text().split()) < 15]
        full_text = random.choice(titles)
        words = [w.strip(",.!'\"") for w in full_text.split() if len(w.strip(",.!'\"")) >= 5]
        answer = random.choice(words)
        return {"text": full_text, "answer": answer, "ko": translate_to_ko(full_text), "word_ko": translate_to_ko(answer)}
    except: return None

# --- 5. ✍️ 메인 화면 로직 ---
st.markdown('<div class="main-wrapper">', unsafe_allow_html=True)
st.title("🌟 BBC 뉴스 영어 퀴즈")

if 'registered_nickname' not in st.session_state:
    display_ranking()
    st.subheader("닉네임 입력 🐼")
    nick = st.text_input("nickname", label_visibility="collapsed", placeholder="닉네임을 입력하세요...")
    if st.button("게임 시작"):
        if nick.strip():
            st.session_state.registered_nickname = nick.strip()
            user_doc = db.collection("quiz_users").document(st.session_state.registered_nickname).get()
            if user_doc.exists:
                d = user_doc.to_dict()
                st.session_state.score = d.get("score", 0) if d.get("last_date") == today else 0
            else:
                st.session_state.score = 0
            st.rerun()
else:
    st.markdown(f"### 🔥 **{st.session_state.registered_nickname}**님 ({st.session_state.score}점)")
    
    if 'current_quiz' not in st.session_state:
        st.session_state.show_hint = False
        st.session_state.wrong_count = 0 # 오답 횟수 초기화
        st.session_state.game_over = False
        with st.spinner("최신 뉴스 가져오는 중..."):
            q = get_bbc_quiz()
            if q: st.session_state.current_quiz = q
            else: st.error("뉴스를 불러오지 못했습니다.")

    if 'current_quiz' in st.session_state:
        q = st.session_state.current_quiz
        ans = q['answer']
        
        # 기회 표시
        st.markdown(f"<p style='color:#FF6347; font-weight:bold;'>❤️ 남은 기회: {3 - st.session_state.wrong_count}번</p>", unsafe_allow_html=True)

        # 단어 표시 로직 (정답 공개 시에는 정답 전체 노출)
        if st.session_state.game_over:
            display_word = ans
        else:
            display_word = (ans[0] + " _" * (len(ans) - 1)) if st.session_state.show_hint else ("_ " * len(ans))
        
        display_text = q['text'].replace(ans, f" [ {display_word} ] ")
        
        st.markdown(f'<div class="quiz-card"><h4>{display_text}</h4><p style="color:#AAA; font-size:0.9rem; margin-top:10px; border-top:1px solid #444; padding-top:15px;">💡 {q["ko"]}</p></div>', unsafe_allow_html=True)
        
        if st.session_state.show_hint:
            st.info(f"🔍 단어 뜻: {q['word_ko']}")
        
        if st.session_state.game_over:
            st.warning(f"🚫 3번 틀렸습니다! 정답은 '{ans}'입니다.")
            if st.button("⏭️ 다음 문제로 넘어가기"):
                del st.session_state.current_quiz
                st.rerun()
        else:
            user_ans = st.text_input("정답 입력:", key="quiz_input", placeholder="영단어를 입력하세요")
            
            # 버튼 3종 세트 (상시 노출)
            btn_col1, btn_col2, btn_col3 = st.columns(3)
            with btn_col1:
                if st.button("✅ 확인"):
                    if user_ans.lower().strip() == ans.lower().strip():
                        st.balloons()
                        st.session_state.score += 1
                        db.collection("quiz_users").document(st.session_state.registered_nickname).set({
                            "score": st.session_state.score, "last_date": today
                        })
                        del st.session_state.current_quiz
                        st.rerun()
                    else:
                        st.markdown('<div class="wrong-x">❌</div>', unsafe_allow_html=True)
                        st.session_state.wrong_count += 1
                        if st.session_state.wrong_count >= 3:
                            st.session_state.game_over = True
                        time.sleep(0.5)
                        st.rerun()
            with btn_col2:
                if st.button("💡 힌트"):
                    st.session_state.show_hint = True
                    st.rerun()
            with btn_col3:
                if st.button("⏭️ 패스"):
                    del st.session_state.current_quiz
                    st.rerun()
    
    st.write("---")
    display_ranking()

st.markdown('</div>', unsafe_allow_html=True)