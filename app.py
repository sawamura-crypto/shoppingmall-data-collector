"""
에이블리 파트너스 데이터 수집 프로그램 (Streamlit 웹앱)

실행 방법: 터미널에서 아래 명령어 입력
    streamlit run app.py

구조:
- 로그인 화면에서 ID/PW 입력
- 가져올 데이터 종류 선택 (현재는 "리뷰"만 지원, 추후 확장 예정)
- 수집된 데이터를 화면에 표로 바로 보여줌 (엑셀 강제 저장 없음, 원하면 다운로드 버튼으로 받을 수 있음)
"""

import streamlit as st
import pandas as pd
import subprocess
import sys
from playwright.sync_api import sync_playwright


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

# 실제 데이터 행에서 확인된 칸 순서 (0번부터):
# [0] 상품번호, [1] 대표이미지(텍스트 없음, 사용 안 함), [2] 상품명,
# [3] 리뷰번호, [4] 리뷰내용, [5] 최근수정일시, [6] 상품주문번호
COLUMN_INDEX = {
    "상품번호": 0,
    "상품명": 2,
    "리뷰번호": 3,
    "리뷰내용": 4,
    "최근수정일시": 5,
    "상품주문번호": 6,
}

st.set_page_config(page_title="마켓인사이트", page_icon="📊", layout="wide")


# ---------- 데이터 수집 관련 함수 (기존 스크래핑 로직 재사용) ----------

def login(page, ably_id, ably_password):
    page.goto("https://my.a-bly.com/login/")
    page.get_by_role("textbox", name="이메일").click()
    page.get_by_role("textbox", name="이메일").fill(ably_id)
    page.get_by_role("textbox", name="비밀번호").click()
    page.get_by_role("textbox", name="비밀번호").fill(ably_password)
    page.get_by_role("button", name="로그인").click()
    page.wait_for_timeout(4000)


def go_to_reviews_and_set_page_size(page, page_size=100):
    page.goto("https://my.a-bly.com/reviews")
    page.wait_for_timeout(3000)
    try:
        page.get_by_role("textbox", name="선택").click()
        page.wait_for_timeout(500)
        page.get_by_text(f"{page_size}개씩 보기").click()
        page.wait_for_timeout(1500)
    except Exception:
        pass


def extract_rows_from_current_page(page):
    rows = page.locator(".el-table__body tbody tr.el-table__row")
    row_count = rows.count()
    results = []

    for r in range(row_count):
        row = rows.nth(r)
        cells = row.locator("td")
        cell_count = cells.count()

        record = {}
        for key, col_idx in COLUMN_INDEX.items():
            if col_idx >= cell_count:
                record[key] = ""
                continue
            try:
                record[key] = cells.nth(col_idx).inner_text().strip()
            except Exception:
                record[key] = ""

        results.append(record)

    return results


def go_to_next_page(page):
    try:
        next_btn = page.locator("button.btn-next")
        if next_btn.is_disabled():
            return False
        next_btn.click()
        page.wait_for_timeout(1500)
        return True
    except Exception:
        return False


def collect_reviews(ably_id, ably_password, target_count, progress_callback=None):
    """리뷰를 target_count개만큼 수집. progress_callback(현재까지 수집된 개수)로 진행상황 전달."""
    all_results = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)  # 화면 없이 백그라운드 실행
        context = browser.new_context()
        page = context.new_page()

        login(page, ably_id, ably_password)
        go_to_reviews_and_set_page_size(page, page_size=100)

        while len(all_results) < target_count:
            page_data = extract_rows_from_current_page(page)
            if not page_data:
                break

            all_results.extend(page_data)
            if progress_callback:
                progress_callback(min(len(all_results), target_count))

            if len(all_results) >= target_count:
                break

            has_next = go_to_next_page(page)
            if not has_next:
                break

        context.close()
        browser.close()

    return all_results[:target_count]


# ---------- Streamlit 화면 구성 ----------

# 세션 상태 초기화 (페이지를 새로고침해도 로그인 정보, 데이터가 유지되도록)
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "ably_id" not in st.session_state:
    st.session_state.ably_id = ""
if "ably_password" not in st.session_state:
    st.session_state.ably_password = ""
if "review_data" not in st.session_state:
    st.session_state.review_data = None


st.title("📊 마켓인사이트")
st.caption("쇼핑몰 파트너스 데이터 수집·분석 도구")

# --- 로그인 영역 ---
with st.sidebar:
    st.markdown("## 📊 마켓인사이트")
    st.divider()
    st.header("🔐 에이블리 로그인")

    if not st.session_state.logged_in:
        ably_id_input = st.text_input("에이블리 ID (이메일)")
        ably_password_input = st.text_input("비밀번호", type="password")

        if st.button("로그인 정보 저장", type="primary"):
            if ably_id_input and ably_password_input:
                st.session_state.ably_id = ably_id_input
                st.session_state.ably_password = ably_password_input
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.warning("ID와 비밀번호를 모두 입력해주세요.")
    else:
        st.success(f"로그인됨: {st.session_state.ably_id}")
        if st.button("로그아웃"):
            st.session_state.logged_in = False
            st.session_state.ably_id = ""
            st.session_state.ably_password = ""
            st.session_state.review_data = None
            st.rerun()


# --- 메인 영역 ---
if not st.session_state.logged_in:
    st.info("왼쪽 사이드바에서 먼저 로그인 정보를 입력해주세요.")
else:
    st.subheader("📋 가져올 데이터 종류 선택")

    data_type = st.selectbox(
        "데이터 종류",
        ["리뷰"],  # 추후 여기에 "매출", "주문" 등 추가 가능
    )

    if data_type == "리뷰":
        col1, col2 = st.columns([3, 1])
        with col1:
            target_count = st.number_input(
                "수집할 리뷰 개수", min_value=1, max_value=10000, value=100, step=10
            )
        with col2:
            st.write("")  # 버튼 위치 맞추기용 여백
            st.write("")
            collect_btn = st.button("리뷰 수집 시작", type="primary")

        if collect_btn:
            progress_bar = st.progress(0, text="수집 준비 중...")

            def update_progress(current):
                pct = min(current / target_count, 1.0)
                progress_bar.progress(pct, text=f"수집 중... ({current}/{target_count})")

            with st.spinner("에이블리 어드민에 접속하여 데이터를 가져오는 중입니다..."):
                try:
                    results = collect_reviews(
                        st.session_state.ably_id,
                        st.session_state.ably_password,
                        int(target_count),
                        progress_callback=update_progress,
                    )
                    st.session_state.review_data = pd.DataFrame(results)
                    progress_bar.progress(1.0, text="수집 완료!")
                    st.success(f"{len(results)}개의 리뷰를 수집했습니다.")
                except Exception as e:
                    st.error(f"수집 중 오류가 발생했습니다: {e}")

    # --- 결과 표시 영역 ---
    if st.session_state.review_data is not None:
        st.subheader("📊 수집된 리뷰 데이터")
        st.dataframe(st.session_state.review_data, use_container_width=True)

        # 원하면 엑셀로도 다운로드 가능하게 (강제 저장이 아니라 선택적 다운로드)
        csv = st.session_state.review_data.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="CSV로 다운로드",
            data=csv,
            file_name="ably_reviews.csv",
            mime="text/csv",
        )
