"""
마켓인사이트 (Streamlit 웹앱)

실행 방법: 터미널에서 아래 명령어 입력
    streamlit run app.py

구조:
- 1단계: 마켓인사이트 자체 로그인 (auth.py)
- 2단계: 쇼핑몰 플랫폼 선택 + 계정 연결 (platforms_ably.py 등)
- 3단계: 데이터 수집 (개수 기준 / 날짜 기준) + 결과 표시
- 리뷰는 긍정/부정/중립 키워드를 기준으로 자동 분류 가능 (classify.py)

플랫폼 확장 방법:
- platforms_ably.py와 동일한 형태(login, collect_reviews_by_count, collect_reviews_by_date)로
  새 파일(예: platforms_zigzag.py)을 만들고, 아래 PLATFORMS 딸셔너리에 등록하면 됩니다.
"""

import streamlit as st
import pandas as pd
import subprocess
import sys
import datetime
from playwright.sync_api import sync_playwright

import auth
import classify
import platforms_ably


# ---------- 플랫폼 레지스트리 (확장 지점) ----------
# 새 쇼핑몰을 추가할 때는 이 딸셔너리에 한 줄만 추가하면 됩니다.
PLATFORMS = {
    "에이블리": platforms_ably,
    # "지그재그": platforms_zigzag,  # 추후 추가 예시
    # "쿠팡": platforms_coupang,    # 추후 추가 예시
}


@st.cache_resource
def install_playwright_browser():
    """Streamlit Cloud 서버에는 Chromium 브라우저가 미리 설치되어 있지 않으므로,
    앱이 처음 켜질 때 한 번만 자동으로 설치합니다."""
    try:
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=True,
            capture_output=True,
        )
        return True
    except Exception as e:
        st.error(f"브라우저 설치 중 오류: {e}")
        return False


install_playwright_browser()

st.set_page_config(page_title="마켓인사이트", page_icon="📊", layout="wide")


def run_collection(platform_module, user_id, password, mode, target_count=None,
                    start_date=None, end_date=None, progress_callback=None, debug_log=None):
    """선택된 플랫폼 모듈을 이용해 실제 수집을 수행하는 공통 함수.
    mode는 'count' 또는 'date'."""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        platform_module.login(page, user_id, password, debug_log=debug_log)

        if mode == "count":
            results = platform_module.collect_reviews_by_count(
                page, target_count, progress_callback=progress_callback, debug_log=debug_log
            )
        else:
            results = platform_module.collect_reviews_by_date(
                page, start_date, end_date, progress_callback=progress_callback, debug_log=debug_log
            )

        context.close()
        browser.close()

    return results


# ---------- 세션 상태 초기화 ----------

auth.init_auth_session_state()

if "platform_logged_in" not in st.session_state:
    st.session_state.platform_logged_in = False
if "platform_name" not in st.session_state:
    st.session_state.platform_name = None
if "platform_user_id" not in st.session_state:
    st.session_state.platform_user_id = ""
if "platform_password" not in st.session_state:
    st.session_state.platform_password = ""
if "review_data" not in st.session_state:
    st.session_state.review_data = None
if "positive_keywords_raw" not in st.session_state:
    st.session_state.positive_keywords_raw = ""
if "negative_keywords_raw" not in st.session_state:
    st.session_state.negative_keywords_raw = ""


# --- 1단계: 마켓인사이트 자체 로그인 ---
if not st.session_state.app_logged_in:
    auth.render_login_page()
    st.stop()


# --- 공통 사이드바 ---
with st.sidebar:
    st.markdown("## 📊 마켓인사이트")
    st.caption(f"{st.session_state.app_username}님 환영합니다")
    st.divider()

    if st.session_state.platform_logged_in:
        st.success(f"{st.session_state.platform_name} 연결됨: {st.session_state.platform_user_id}")
        if st.button("연결 해제"):
            st.session_state.platform_logged_in = False
            st.session_state.platform_name = None
            st.session_state.platform_user_id = ""
            st.session_state.platform_password = ""
            st.session_state.review_data = None
            st.rerun()

    st.divider()
    if st.button("로그아웃"):
        auth.logout()
        st.rerun()


st.title("📊 마켓인사이트")
st.caption("쇼핑몰 파트너스 데이터 수집·분석 도구")


# --- 2단계: 쇼핑몰 플랫폼 선택 + 계정 연결 ---
if not st.session_state.platform_logged_in:
    st.subheader("🔗 쇼핑몰 계정 연결")

    _, center_col, _ = st.columns([1, 1.2, 1])
    with center_col:
        platform_choice = st.selectbox("쇼핑몰 선택", list(PLATFORMS.keys()))
        user_id_input = st.text_input("ID (이메일)")
        password_input = st.text_input("비밀번호", type="password")

        if st.button("연결하기", type="primary", use_container_width=True):
            if user_id_input and password_input:
                st.session_state.platform_name = platform_choice
                st.session_state.platform_user_id = user_id_input
                st.session_state.platform_password = password_input
                st.session_state.platform_logged_in = True
                st.rerun()
            else:
                st.warning("ID와 비밀번호를 모두 입력해주세요.")
    st.stop()


platform_module = PLATFORMS[st.session_state.platform_name]


# --- 3단계: 데이터 수집 ---
st.subheader("📋 가져올 데이터 종류 선택")

data_type = st.selectbox("데이터 종류", ["리뷰"])  # 추후 "매출", "주문" 등 추가 가능

if data_type == "리뷰":
    collection_mode = st.radio("수집 방식", ["개수로 가져오기", "날짜로 가져오기"], horizontal=True)

    target_count = None
    start_date = None
    end_date = None

    if collection_mode == "개수로 가져오기":
        col1, col2 = st.columns([3, 1])
        with col1:
            target_count = st.number_input(
                "수집할 리뷰 개수", min_value=1, max_value=10000, value=100, step=10
            )
        with col2:
            st.write("")
            st.write("")
            collect_btn = st.button("리뷰 수집 시작", type="primary")
    else:
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            start_date_input = st.date_input(
                "시작일", value=datetime.date.today() - datetime.timedelta(days=7)
            )
        with col2:
            end_date_input = st.date_input("종료일", value=datetime.date.today())
        with col3:
            st.write("")
            st.write("")
            collect_btn = st.button("리뷰 수집 시작", type="primary")
        start_date = start_date_input.strftime("%Y-%m-%d")
        end_date = end_date_input.strftime("%Y-%m-%d")

    # --- 긍정/부정 키워드 입력 ---
    with st.expander("🏷️ 긍정/부정 키워드 설정", expanded=False):
        st.caption("쉼표(,) 또는 줄바꿈으로 여러 키워드를 구분해서 입력하세요.")
        kw_col1, kw_col2 = st.columns(2)
        with kw_col1:
            st.session_state.positive_keywords_raw = st.text_area(
                "긍정 키워드", value=st.session_state.positive_keywords_raw,
                placeholder="예: 좋아요, 예뻐요, 편해요, 만족",
                height=100,
            )
        with kw_col2:
            st.session_state.negative_keywords_raw = st.text_area(
                "부정 키워드", value=st.session_state.negative_keywords_raw,
                placeholder="예: 별로, 불편, 실망, 불량",
                height=100,
            )

    if collect_btn:
        progress_bar = st.progress(0, text="수집 준비 중...")

        if collection_mode == "개수로 가져오기":
            def update_progress(current):
                pct = min(current / target_count, 1.0)
                progress_bar.progress(pct, text=f"수집 중... ({current}/{target_count})")
        else:
            def update_progress(current):
                # 날짜 모드는 총 개수를 미리 알 수 없어서, 진행률 대신 누적 개수만 표시
                progress_bar.progress(0.5, text=f"수집 중... (현재까지 {current}개)")

        with st.spinner("쇼핑몰 어드민에 접속하여 데이터를 가져오는 중입니다..."):
            debug_log = []
            results = []
            try:
                results = run_collection(
                    platform_module,
                    st.session_state.platform_user_id,
                    st.session_state.platform_password,
                    mode="count" if collection_mode == "개수로 가져오기" else "date",
                    target_count=int(target_count) if target_count else None,
                    start_date=start_date,
                    end_date=end_date,
                    progress_callback=update_progress,
                    debug_log=debug_log,
                )
                st.session_state.review_data = pd.DataFrame(results)
                progress_bar.progress(1.0, text="수집 완료!")
                st.success(f"{len(results)}개의 리뷰를 수집했습니다.")
            except Exception as e:
                debug_log.append(f"예외 발생: {e}")
                st.error(f"수집 중 오류가 발생했습니다: {e}")

            if debug_log:
                with st.expander("🔍 진단 로그 (문제 발생 시 참고)", expanded=(len(results) == 0)):
                    import base64
                    for line in debug_log:
                        if line.startswith("SCREENSHOT_BASE64:"):
                            img_bytes = base64.b64decode(line.replace("SCREENSHOT_BASE64:", ""))
                            st.image(img_bytes, caption="로그인 시도 시점의 화면", use_container_width=True)
                        else:
                            st.text(line)


# --- 결과 표시 영역 ---
if st.session_state.review_data is not None and not st.session_state.review_data.empty:
    df = st.session_state.review_data.copy()

    positive_keywords = classify.parse_keyword_input(st.session_state.positive_keywords_raw)
    negative_keywords = classify.parse_keyword_input(st.session_state.negative_keywords_raw)

    if positive_keywords or negative_keywords:
        df = classify.classify_dataframe(df, "리뷰내용", positive_keywords, negative_keywords)

    st.subheader("📊 수집된 리뷰 데이터")

    if "감정분류" in df.columns:
        tab_all, tab_pos, tab_neg, tab_neutral, tab_grouped = st.tabs(
            ["전체", "🟢 긍정", "🔴 부정", "⚪ 중립", "📦 상품별 보기"]
        )

        with tab_all:
            st.dataframe(df, use_container_width=True)
        with tab_pos:
            st.dataframe(df[df["감정분류"] == "긍정"], use_container_width=True)
        with tab_neg:
            st.dataframe(df[df["감정분류"] == "부정"], use_container_width=True)
        with tab_neutral:
            st.dataframe(df[df["감정분류"] == "중립"], use_container_width=True)
        with tab_grouped:
            st.caption("같은 상품의 리뷰를 모아서 보여줍니다.")
            for product_name, group in df.groupby("상품명"):
                with st.expander(f"{product_name} ({len(group)}건)"):
                    st.dataframe(group, use_container_width=True)
    else:
        st.info("키워드를 입력하면 긍정/부정/중립으로 자동 분류됩니다.")
        st.dataframe(df, use_container_width=True)

    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="CSV로 다운로드",
        data=csv,
        file_name="reviews.csv",
        mime="text/csv",
    )
