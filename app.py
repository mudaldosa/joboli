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

# --- 1. 🎨 반응형 디자인 설정 (모바일/PC 완벽 최적화) ---
st.set_page_config(page_title="BBC News Quiz", page_icon="🌟", layout="wide")

st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background-color: #0E1117; color: white; }
    [data-testid="stSidebar"] { display: none; }
    h1, h2, h3, h4, p, span { color: white !important; font-family: 'Pretendard', sans-serif; }
    h1 { color: #FFD700 !important; text-align: center; font-weight: bold; margin-bottom: 20px; font-size: 1.8rem !important; }

    .main-wrapper { max-width: 700px; margin: 0 auto; padding: 10px; }

    /* 입력창 디자인: 둥근 모서리와 노란 테두리 */
    .stTextInput > div > div > input {
        background-color: #1A1C23 !important;
        color: white !important;
        border: 2px solid #FFD700 !important;
        border-radius: 12px !important;
        padding: 12px 15px !important;
        font-size: 1.1rem !important;
    }

    /* 버튼 디자인: 터치하기 편한 크기 */
    .stButton > button {
        background-color: #FFD700 !important;
        color: #0E1117 !important;
        font-weight: bold !important;
        border-radius: 12px !important;
        width: 100% !important;
        height: 48px !important;
        font-size: 0.95rem !important;
        border: none !important;
        margin-top: 5px;
    }

    /* 🏆 실시간 순위 박스 */
    .ranking-container {
        background-color: #1A1C23; border: 2px solid #FFD700;
        border-radius: 15px; padding: 15px; margin-bottom: 20px;
    }
    .ranking-title { color: #FFD700 !important; font-weight: bold; text-align: center; border-bottom: 1px solid #444; margin-bottom: 10px; padding-bottom: 5px; }
    .ranking-item { display: flex; justify-content: space-between; margin-bottom: 5px; font-size: 0.95rem; border-bottom: 1px dashed #333; padding-bottom: 3px; }

    /* 퀴즈 카드 디자인 */
    .quiz-card { background-color: #262730; border-radius: 20px; padding: 25px; border: 1px solid #444; margin-bottom: 15px; }

    /* ❌ 오답 시 커다란 X 애니메이션 */
    .wrong-x {
        position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
        font-size: 12rem; color: #FF6347; z-index: 10000; animation: fade-out 1s forwards; pointer-events: none;
    }
    @keyframes fade-out { 0% {opacity: 1; transform: translate(-50%, -50%) scale(1.2);} 100% {opacity: 0; transform: translate(-50%, -50%) scale(0.8);} }
</style>
""", unsafe_allow_html=True)

# --- 2. 🌍 한국 표준시(KST) 및 DB 설정 ---
KST = pytz.timezone('Asia/Seoul')
today = datetime.now(KST).strftime("%Y-%m-%d")

if "db" not in st.session_state:
    key_dict = json.loads(st.secrets["firebase"]["info"])
    creds = service_account.Credentials.from_service_account_info(key_dict)
    st.session_state.db = firestore.Client(credentials=creds)

db = st.session_state.db

# --- 3. 🏆 랭킹 시스템 (실시간 정렬) ---
def display_ranking():
    st.markdown('<div class="ranking-container"><div class="ranking-title">🏆 오늘의 TOP 5</div>', unsafe_allow_html=True)
    try:
        # 오늘 날짜 데이터 50개 가져오기
        docs = db.collection("quiz_users").where("last_date", "==", today).limit(50).stream()
        data = [d.to_dict() | {"name": d.id} for d in docs]
        # 파이썬에서 직접 점수순 정렬 (색인 에러 방지)
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

# --- 4. 🧠 퀴즈 엔진 (고유명사 필터링 + 중복 방지) ---
def translate_to_ko(text):
    try:
        url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=ko&dt=t&q=" + urllib.parse.quote(text)
        return requests.get(url).json()[0][0][0]
    except: return "번역 실패"

def get_bbc_quiz():
    try:
        # 뉴스 섹션 다양화 (중복 방지 극대화)
        sections = ["", "/world", "/business", "/technology", "/science_and_environment", "/health", "/entertainment_and_arts"]
        random.shuffle(sections)
        
        for section in sections:
            url = f"https://www.bbc.com/news{section}"
            soup = BeautifulSoup(requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).text, 'html.parser')
            
            # h2와 h3를 모두 긁어서 문제 풀 확보
            titles = [h.get_text().strip() for h in soup.find_all(['h2', 'h3']) if 7 < len(h.get_text().split()) < 15]
            random.shuffle(titles)
            
            for title in titles:
                # 사용자가 이미 풀어본 제목(ID)인지 확인
                if title[:25] not in st.session_state.get('solved', []):
                    words = []
                    original_words = title.split()
                    for i, w in enumerate(original_words):
                        clean_w = w.strip(",.!'\"")
                        # 길이 5자 이상 & 고유명사(대문자 이름) 필터링
                        if len(clean_w) >= 5 and (i == 0 or clean_w[0].islower()):
                            words.append(clean_w)
                    
                    if words:
                        answer = random.choice(words)
                        return {"id": title[:25], "text": title, "answer": answer, "ko": translate_to_ko(title), "word_ko": translate_to_ko(answer)}
        return None
    except: return None

# --- 5. ✍️ 메인 화면 구성 ---
st.markdown('<div class="main-wrapper">', unsafe_allow_html=True)
st.title("🌟 BBC 뉴스 영어 퀴즈")

# 로그인 전
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
                st.session_state.solved = d.get("solved_ids", [])
            else:
                st.session_state.score = 0
                st.session_state.solved = []
            st.rerun()

# 로그인 후 (게임 화면)
else:
    st.markdown(f"### 🔥 **{st.session_state.registered_nickname}**님 ({st.session_state.score}점)")
    
    if 'current_quiz' not in st.session_state:
        st.session_state.show_hint = False
        st.session_state.wrong_count = 0
        st.session_state.game_over = False
        # ✅ 새 문제 시 입력창 자동 초기화
        if "quiz_input" in st.session_state: st.session_state["quiz_input"] = ""
            
        with st.spinner("최신 뉴스 분석 중..."):
            q = get_bbc_quiz()
            if q: st.session_state.current_quiz = q
            else: st.error("모든 뉴스를 정복하셨거나 연결이 불안정합니다!")

    if 'current_quiz' in st.session_state:
        q = st.session_state.current_quiz
        ans = q['answer']
        
        st.markdown(f"<p style='color:#FF6347; font-weight:bold;'>❤️ 남은 기회: {3 - st.session_state.wrong_count}번</p>", unsafe_allow_html=True)

        display_word = ans if st.session_state.game_over else ((ans[0] + " _" * (len(ans) - 1)) if st.session_state.show_hint else "_ " * len(ans))
        display_text = q['text'].replace(ans, f" [ {display_word} ] ")
        
        st.markdown(f'<div class="quiz-card"><h4>{display_text}</h4><p style="color:#AAA; font-size:0.9rem; margin-top:10px; border-top:1px solid #444; padding-top:10px;">💡 {q["ko"]}</p></div>', unsafe_allow_html=True)
        
        if st.session_state.show_hint: st.info(f"🔍 단어 뜻: {q['word_ko']}")
        
        if st.session_state.game_over:
            st.warning(f"🚫 3번 틀렸습니다! 정답은 '{ans}'입니다.")
            if st.button("⏭️ 다음 문제로 넘어가기"):
                st.session_state.solved.append(q['id'])
                del st.session_state.current_quiz
                st.rerun()
        else:
            user_ans = st.text_input("정답 입력:", key="quiz_input", placeholder="영단어를 입력하세요")
            
            btn_col1, btn_col2, btn_col3 = st.columns(3)
            with btn_col1:
                if st.button("✅ 확인"):
                    if user_ans.lower().strip() == ans.lower().strip():
                        st.balloons()
                        st.session_state.score += 1
                        st.session_state.solved.append(q['id'])
                        db.collection("quiz_users").document(st.session_state.registered_nickname).set({
                            "score": st.session_state.score, "last_date": today, "solved_ids": st.session_state.solved
                        })
                        del st.session_state.current_quiz
                        st.rerun()
                    else:
                        st.markdown('<div class="wrong-x">❌</div>', unsafe_allow_html=True)
                        st.session_state.wrong_count += 1
                        if st.session_state.wrong_count >= 3: st.session_state.game_over = True
                        time.sleep(0.5); st.rerun()
            with btn_col2:
                if st.button("💡 힌트"):
                    st.session_state.show_hint = True; st.rerun()
            with btn_col3:
                if st.button("⏭️ 패스"):
                    st.session_state.solved.append(q['id'])
                    del st.session_state.current_quiz; st.rerun()
    
    st.write("---")
    display_ranking()

st.markdown('</div>', unsafe_allow_html=True)