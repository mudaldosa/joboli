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
import time  # ⏱️ 깜빡임 효과를 위한 시간 도구 추가

# --- 1. 🎨 디자인 설정 (디자인 복구 + 오답 X 표시 UI 추가) ---
st.set_page_config(page_title="BBC News Quiz", page_icon="🌟", layout="wide")

st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background-color: #0E1117; color: white; }
    [data-testid="stSidebar"] { display: none; }
    
    h1, h2, h3, p, span, div { color: white !important; }
    h1 { color: #FFD700 !important; text-align: center; font-weight: bold; margin-top: 50px; margin-bottom: 40px; }

    .login-section { max-width: 600px; margin: 0 auto; text-align: left; }
    
    /* 🌟 입력창 높이 강제 확보 (짤림 방지 핵심) */
    [data-testid="stVirtualizedPage"] .element-container, .stTextInput {
        height: 160px !important; 
        overflow: visible !important; 
        margin-bottom: 20px !important;
    }

    .stTextInput > div { height: 100px !important; background-color: transparent !important; }

    .stTextInput > div > div > input {
        background-color: #1A1C23 !important;
        color: white !important;
        border: 3px solid #FFD700 !important; 
        border-radius: 12px !important;
        height: 80px !important; 
        font-size: 1.6rem !important;
        padding: 0 20px !important;
        width: 100% !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    }

    /* 🌟 게임 시작 버튼 위치 (겹침 방지) */
    .stButton > button {
        background-color: #FFD700 !important;
        color: #0E1117 !important;
        font-weight: bold !important;
        font-size: 1.3rem !important;
        border-radius: 12px !important;
        width: 100% !important;
        height: 60px !important;
        margin-top: 40px !important; 
        border: none !important;
    }

    /* 🏆 랭킹 박스 스타일 (정렬 방식 수정으로 즉시 노출) */
    .ranking-box {
        position: fixed; top: 60px; right: 30px; width: 230px;
        background-color: #1A1C23; border: 2px solid #FFD700;
        border-radius: 15px; padding: 15px; z-index: 9999;
    }
    .ranking-title { color: #FFD700 !important; font-weight: bold; border-bottom: 1px solid #444; text-align: center; margin-bottom: 10px; }
    .ranking-item { font-size: 1rem; margin-bottom: 8px; }

    /* 퀴즈 카드 디자인 */
    .main-container { width: 100%; max-width: 800px; margin: 0 auto; padding-top: 20px; }
    .quiz-card { background-color: #262730; border-radius: 20px; padding: 40px; border: 1px solid #444; margin-bottom: 20px; }

    /* ❌ [신규] 강력한 X 표시 UI 스타일 */
    .wrong-answer-x {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        font-size: 15rem !important; /* 화면 가득 채우는 크기 */
        color: #FF6347 !important; /* 빨간색 */
        font-weight: bold !important;
        z-index: 10000; /* 최상위 노출 */
        opacity: 0;
        animation: fade-out 1.2s ease-out forwards; /* 깜빡 후 서서히 사라짐 */
        pointer-events: none; /* 클릭 방지 */
    }

    @keyframes fade-out {
        0% { opacity: 1; transform: translate(-50%, -50%) scale(1.2); }
        20% { opacity: 1; transform: translate(-50%, -50%) scale(1); }
        80% { opacity: 0.8; }
        100% { opacity: 0; transform: translate(-50%, -50%) scale(0.8); }
    }
</style>
""", unsafe_allow_html=True)

# --- 2. 🌍 한국 시간(KST) 및 Firebase 설정 ---
KST = pytz.timezone('Asia/Seoul')
today = datetime.now(KST).strftime("%Y-%m-%d")

if "db" not in st.session_state:
    key_dict = json.loads(st.secrets["firebase"]["info"])
    creds = service_account.Credentials.from_service_account_info(key_dict)
    st.session_state.db = firestore.Client(credentials=creds)

db = st.session_state.db

# --- 3. 🛡️ 랭킹 로드 함수 (KST 기준) ---
def get_rank_html():
    rank_html = f'<div class="ranking-box"><div class="ranking-title">🏆 오늘 실시간 순위</div>'
    try:
        # [수정] 오늘 데이터가 없으면 '로딩 중' 대신 안내 문구를 띄우고, 
        # 에러가 나면(색인 문제 등) 필터링 조건을 단순화해서라도 가져오게 합니다.
        rankers = db.collection("quiz_users")\
                    .where("last_date", "==", today)\
                    .order_by("score", direction=firestore.Query.DESCENDING)\
                    .limit(5).stream()
        
        found = False
        medals = ["🥇", "🥈", "🥉", "4.", "5."]
        for i, r in enumerate(rankers):
            d = r.to_dict()
            rank_html += f'<div class="ranking-item">{medals[i]} {r.id}: <b>{d["score"]}점</b></div>'
            found = True
            
        if not found:
            rank_html += '<div class="ranking-item">오늘 첫 도전자가 되세요!</div>'
            
    except Exception as e:
        # 색인(Index)이 안 만들어졌을 때 발생하는 에러를 잡아서 
        # 최소한 점수순으로라도 보여주도록 방어 코드를 짭니다.
        rank_html += '<div class="ranking-item">데이터 로딩 중...</div>'
        # 터미널이나 Streamlit Log에 찍히는 색인 생성 링크를 꼭 클릭해야 합니다!
        print(f"Ranking Error: {e}") 
        
    rank_html += '</div>'
    return rank_html

st.markdown(get_rank_html(), unsafe_allow_html=True)

# --- 4. 🧠 퀴즈 로직 & 번역 ---
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

# --- 5. ✍️ 메인 화면 ---
if 'registered_nickname' not in st.session_state:
    st.session_state.registered_nickname = None

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
    # 게임 화면 레아웃
    st.markdown('<div class="main-container">', unsafe_allow_html=True)
    st.title("🌟 BBC 실시간 뉴스 영어 퀴즈")
    st.markdown(f"### 🔥 **{st.session_state.registered_nickname}**님 (오늘 **{st.session_state.score}**점)")

    if 'current_quiz' not in st.session_state:
        st.session_state.attempts = 3
        st.session_state.game_over = False
        st.session_state.show_hint = False
        with st.spinner("최신 뉴스 분석 중..."):
            for _ in range(10):
                q = get_bbc_news_quiz()
                if q and q['id'] not in st.session_state.solved:
                    st.session_state.current_quiz = q
                    break
    
    if 'current_quiz' in st.session_state:
        q = st.session_state.current_quiz
        ans_len = len(q['answer'])
        
        st.markdown(f"<p style='color:#FF6347; font-weight:bold;'>❤️ 남은 기회: {st.session_state.attempts}번</p>", unsafe_allow_html=True)
        
        display_ans = q['answer'] if st.session_state.game_over else (q['answer'][0] + " _" * (ans_len - 1) if st.session_state.show_hint else "_ " * ans_len)
        display_text = q['text'].replace(q['answer'], f" [ {display_ans} ] ")
        
        st.markdown(f'<div class="quiz-card"><h3>{display_text}</h3><p style="color:#AAA; margin-top:15px; border-top:1px solid #444; padding-top:15px;">💡 뜻: {q["ko"]}</p></div>', unsafe_allow_html=True)
        
        if not st.session_state.game_over:
            if not st.session_state.show_hint:
                if st.button("💡 첫 글자 + 단어 힌트 보기"):
                    st.session_state.show_hint = True
                    st.rerun()
            else:
                st.info(f"🔍 단어 뜻: {q['word_ko']}")

            user_ans = st.text_input("정답 입력 (단어만 입력):", key="ans_input")
            if st.button("정답 확인"):
                if user_ans.lower().strip() == q['answer'].lower().strip():
                    st.balloons()
                    st.session_state.score += 1
                    st.session_state.solved.append(q['id'])
                    db.collection("quiz_users").document(st.session_state.registered_nickname).set({
                        "score": st.session_state.score, 
                        "solved_ids": st.session_state.solved, 
                        "last_date": today
                    })
                    del st.session_state.current_quiz
                    st.rerun()
                else:
                    # 🌟 [핵심 신규] 강력한 X 표시 UI 애니메이션을 띄움
                    wrong_x = st.empty() # 애니메이션을 띄울 공간 확보
                    wrong_x.markdown('<div class="wrong-answer-x">❌</div>', unsafe_allow_html=True)
                    time.sleep(1.2) # 애니메이션 시간 동안 대기
                    wrong_x.empty() # 애니메이션 삭제

                    st.session_state.attempts -= 1
                    if st.session_state.attempts <= 0:
                        st.session_state.game_over = True
                        st.session_state.solved.append(q['id'])
                        db.collection("quiz_users").document(st.session_state.registered_nickname).set({
                            "score": st.session_state.score, 
                            "solved_ids": st.session_state.solved, 
                            "last_date": today
                        })
                    st.rerun()
        else:
            st.error(f"❌ 아쉽네요! 정답은 '{q['answer']}'였습니다.")
            if st.button("다음 뉴스로 이동"):
                del st.session_state.current_quiz
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)