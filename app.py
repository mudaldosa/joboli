import streamlit as st
import requests
from bs4 import BeautifulSoup
from google.cloud import firestore
from google.oauth2 import service_account
import json
import random
from datetime import datetime
import urllib.parse

# --- 1. 🎨 디자인 설정 (컨테이너 높이 강제 확보) ---
st.set_page_config(page_title="BBC News Quiz", page_icon="🌟", layout="wide")

st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background-color: #0E1117; color: white; }
    [data-testid="stSidebar"] { display: none; }
    
    h1, h2, h3, p, span, div { color: white !important; }
    h1 { color: #FFD700 !important; text-align: center; font-weight: bold; margin-top: 50px; margin-bottom: 40px; }

    /* 🌟 로그인 영역 */
    .login-section {
        max-width: 600px;
        margin: 0 auto;
        text-align: left;
    }
    
    /* 🌟 [최종 해결책] 부모 요소의 높이를 강제로 늘려서 잘림 방지 */
    [data-testid="stVirtualizedPage"] .element-container,
    .stTextInput {
        height: 160px !important; /* 박스 전체가 들어갈 높이를 아예 고정 */
        overflow: visible !important; /* 넘치는 부분이 보여야 함 */
        margin-bottom: 20px !important;
    }

    .stTextInput > div {
        height: 100px !important; /* 입력창 자체의 높이 확보 */
        background-color: transparent !important;
    }

    .stTextInput > div > div > input {
        background-color: #1A1C23 !important;
        color: white !important;
        border: 3px solid #FFD700 !important; /* 테두리를 더 확실하게 3px로 */
        border-radius: 12px !important;
        
        height: 80px !important; /* 입력창 내부 높이 */
        font-size: 1.6rem !important;
        padding: 0 20px !important;
        
        width: 100% !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3); /* 아래쪽 그림자를 줘서 입체감 부여 */
    }

    /* 버튼 위치 */
    .stButton > button {
        background-color: #FFD700 !important;
        color: #0E1117 !important;
        font-weight: bold !important;
        font-size: 1.3rem !important;
        border-radius: 12px !important;
        width: 100% !important;
        height: 60px !important;
        margin-top: 20px !important;
        border: none !important;
    }

    .ranking-box {
        position: fixed; top: 60px; right: 30px; width: 220px;
        background-color: #1A1C23; border: 2px solid #FFD700;
        border-radius: 15px; padding: 15px; z-index: 9999;
    }
    .ranking-title { color: #FFD700 !important; font-weight: bold; border-bottom: 1px solid #444; text-align: center; margin-bottom: 10px; }
    .ranking-item { font-size: 1rem; margin-bottom: 8px; }

    .main-container { width: 100%; max-width: 800px; margin: 0 auto; padding-top: 20px; }
</style>
""", unsafe_allow_html=True)

# --- 2. 🔥 Firebase & 랭킹 ---
if "db" not in st.session_state:
    key_dict = json.loads(st.secrets["firebase"]["info"])
    creds = service_account.Credentials.from_service_account_info(key_dict)
    st.session_state.db = firestore.Client(credentials=creds)

db = st.session_state.db
today = datetime.now().strftime("%Y-%m-%d")

def get_rank_html():
    rank_html = f'<div class="ranking-box"><div class="ranking-title">🏆 실시간 순위</div>'
    try:
        rankers = db.collection("quiz_users").where("last_date", "==", today).order_by("score", direction=firestore.Query.DESCENDING).limit(5).stream()
        found = False
        for i, r in enumerate(rankers):
            d = r.to_dict()
            medals = ["🥇", "🥈", "🥉", "4.", "5."]
            rank_html += f'<div class="ranking-item">{medals[i]} {r.id}: {d["score"]}점</div>'
            found = True
        if not found: rank_html += '<div class="ranking-item">첫 도전자가 되세요!</div>'
    except: rank_html += '<div class="ranking-item">로딩 중...</div>'
    rank_html += '</div>'
    return rank_html

st.markdown(get_rank_html(), unsafe_allow_html=True)

if 'registered_nickname' not in st.session_state:
    st.session_state.registered_nickname = None

def translate_to_ko(text):
    try:
        url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=ko&dt=t&q=" + urllib.parse.quote(text)
        return requests.get(url).json()[0][0][0]
    except: return "번역 실패"

def get_bbc_news_quiz():
    try:
        url = "https://www.bbc.com/news"
        soup = BeautifulSoup(requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).text, 'html.parser')
        titles = [h.get_text().strip() for h in soup.find_all('h2') if 7 < len(h.get_text().split()) < 15]
        full_text = random.choice(titles)
        words = [w.strip(",.!'\"") for w in full_text.split() if len(w.strip(",.!'\"")) >= 5]
        answer = random.choice(words)
        return {"id": full_text[:30], "text": full_text, "answer": answer, "ko": translate_to_ko(full_text), "word_ko": translate_to_ko(answer)}
    except: return None

# --- 3. ✍️ 메인 로직 ---
if not st.session_state.registered_nickname:
    st.title("🌟 BBC 실시간 뉴스 영어 퀴즈")
    st.markdown('<div class="login-section">', unsafe_allow_html=True)
    st.subheader("닉네임을 입력하세요 🐼") 
    nickname_input = st.text_input("닉네임", label_visibility="collapsed", placeholder="여기에 닉네임 입력...")
    if st.button("게임 시작하기"):
        if nickname_input.strip():
            st.session_state.registered_nickname = nickname_input.strip()
            user_ref = db.collection("quiz_users").document(st.session_state.registered_nickname).get()
            if user_ref.exists:
                d = user_ref.to_dict()
                st.session_state.score = d.get("score", 0) if d.get("last_date") == today else 0
                st.session_state.solved = d.get("solved_ids", [])
            else:
                st.session_state.score = 0
                st.session_state.solved = []
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
else:
    # 게임 화면
    st.markdown('<div class="main-container">', unsafe_allow_html=True)
    st.title("🌟 BBC 실시간 뉴스 영어 퀴즈")
    st.markdown(f"### 🔥 **{st.session_state.registered_nickname}**님 (오늘 **{st.session_state.score}**점)")

    if 'current_quiz' not in st.session_state:
        st.session_state.attempts = 3
        st.session_state.game_over = False
        st.session_state.show_hint = False
        with st.spinner("최신 뉴스 가져오는 중..."):
            for _ in range(10):
                q = get_bbc_news_quiz()
                if q and q['id'] not in st.session_state.solved:
                    st.session_state.current_quiz = q
                    break
    
    if 'current_quiz' in st.session_state:
        q = st.session_state.current_quiz
        ans_len = len(q['answer'])
        if not st.session_state.game_over:
            st.markdown(f"<p class='chance-text'>❤️ 남은 기회: {st.session_state.attempts}번</p>", unsafe_allow_html=True)
        
        display_ans = q['answer'] if st.session_state.game_over else (q['answer'][0] + " _" * (ans_len - 1) if st.session_state.show_hint else "_ " * ans_len)
        display_text = q['text'].replace(q['answer'], f" [ {display_ans} ] ")
        st.markdown(f'<div style="background:#262730; border-radius:20px; padding:40px; border:1px solid #444; margin-bottom:20px;"><h3>{display_text}</h3><div style="color:#AAA; margin-top:15px; border-top:1px solid #444; padding-top:15px;">💡 뜻: {q["ko"]}</div></div>', unsafe_allow_html=True)
        
        if not st.session_state.game_over:
            if not st.session_state.show_hint:
                if st.button("💡 힌트 보기"):
                    st.session_state.show_hint = True
                    st.rerun()
            else:
                st.markdown(f"<div style='background:#1A1C23; border:1px dashed #FFD700; padding:15px; border-radius:10px; margin:15px 0; color:#FFD700; font-weight:bold;'>🔍 단어 뜻: {q['word_ko']}</div>", unsafe_allow_html=True)

            user_ans = st.text_input("정답 입력:", key="ans_input")
            if st.button("정답 확인"):
                if user_ans.lower().strip() == q['answer'].lower().strip():
                    st.balloons()
                    st.session_state.score += 1
                    st.session_state.solved.append(q['id'])
                    db.collection("quiz_users").document(st.session_state.registered_nickname).set({"score": st.session_state.score, "solved_ids": st.session_state.solved, "last_date": today})
                    del st.session_state.current_quiz
                    st.rerun()
                else:
                    st.session_state.attempts -= 1
                    if st.session_state.attempts <= 0:
                        st.session_state.game_over = True
                        st.session_state.solved.append(q['id'])
                        db.collection("quiz_users").document(st.session_state.registered_nickname).set({"score": st.session_state.score, "solved_ids": st.session_state.solved, "last_date": today})
                    st.rerun()
        else:
            st.error(f"❌ 정답: '{q['answer']}'")
            if st.button("다음 문제"):
                del st.session_state.current_quiz
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)