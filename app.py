"""
마켓인사이트 (Streamlit 웹앱)

실행 방법: 터미널에서 아래 명령어 입력
    streamlit run app.py

구조:
- 1단계: 마켓인사이트 자체 로그인 (auth.py)
- 2단계: 리뷰 데이터 파일 업로드 (로컬 PC의 collect_reviews.py로 수집한 xlsx/csv 파일)
- 3단계: 긍정/부정/중립 키워드 분류 + 상품별 그룹화 + 결과 표시 (ERP 스타일 대시보드)

※ 데이터 "수집"은 로컬 PC에서 collector_app.py로 진행하고, 이 앱에는 그 결과 파일만
   업로드하여 분석합니다 (클라우드에서는 쇼핑몰 자동 로그인이 차단되기 때문).
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

import auth
import classify
import theme


st.set_page_config(page_title="마켓인사이트", page_icon="📊", layout="wide")
theme.inject()


def load_uploaded_file(uploaded_file):
    """업로드된 xlsx 또는 csv 파일을 데이터프레임으로 읽어들입니다."""
    if uploaded_file.name.lower().endswith(".csv"):
        return pd.read_csv(uploaded_file)
    else:
        return pd.read_excel(uploaded_file)


def sentiment_donut_chart(counts: dict):
    """긍정/부정/중립 비율을 보여주는 도넛 차트."""
    labels = list(counts.keys())
    values = list(counts.values())
    colors = [theme.COLORS["positive"], theme.COLORS["negative"], theme.COLORS["neutral"]]

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.65,
                marker=dict(colors=colors, line=dict(color="#FFFFFF", width=2)),
                textinfo="label+percent",
                textfont=dict(size=13),
            )
        ]
    )
    fig.update_layout(
        showlegend=False,
        margin=dict(t=10, b=10, l=10, r=10),
        height=260,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


# ---------- 세션 상태 초기화 ----------

auth.init_auth_session_state()

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
    st.markdown('<div class="sidebar-logo">📊 마켓인사이트</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="sidebar-user">{st.session_state.app_username}님 환영합니다</div>',
        unsafe_allow_html=True,
    )
    st.divider()

    if st.session_state.review_data is not None:
        if st.button("🗑️ 불러온 데이터 지우기", use_container_width=True):
            st.session_state.review_data = None
            st.rerun()

    st.divider()
    if st.button("로그아웃", use_container_width=True):
        auth.logout()
        st.rerun()


st.title("📊 마켓인사이트")
st.caption("쇼핑몰 파트너스 데이터 수집·분석 도구")


# --- 2단계: 파일 업로드 ---
with st.container(border=True):
    st.subheader("📂 리뷰 데이터 불러오기")
    st.caption("로컬 PC에서 collector_app.py로 수집한 엑셀(.xlsx) 또는 CSV 파일을 업로드해주세요.")
    uploaded_file = st.file_uploader("리뷰 파일 업로드", type=["xlsx", "csv"], label_visibility="collapsed")

    if uploaded_file is not None:
        try:
            df_uploaded = load_uploaded_file(uploaded_file)
            st.session_state.review_data = df_uploaded
            st.success(f"{len(df_uploaded)}개의 리뷰를 불러왔습니다.")
        except Exception as e:
            st.error(f"파일을 읽는 중 오류가 발생했습니다: {e}")


# --- 3단계: 긍정/부정 키워드 입력 + 결과 표시 ---
if st.session_state.review_data is not None and not st.session_state.review_data.empty:
    df = st.session_state.review_data.copy()

    review_column = "리뷰내용" if "리뷰내용" in df.columns else None
    if review_column is None:
        st.warning(
            "업로드한 파일에서 '리뷰내용' 컬럼을 찾지 못했습니다. "
            "collector_app.py로 만든 파일 형식인지 확인해주세요."
        )
    else:
        with st.container(border=True):
            st.subheader("🏷️ 긍정/부정 키워드 설정")
            st.caption("쉼표(,) 또는 줄바꿈으로 여러 키워드를 구분해서 입력하세요.")
            kw_col1, kw_col2 = st.columns(2)
            with kw_col1:
                st.session_state.positive_keywords_raw = st.text_area(
                    "긍정 키워드", value=st.session_state.positive_keywords_raw,
                    placeholder="예: 좋아요, 예뻐요, 편해요, 만족",
                    height=90,
                )
            with kw_col2:
                st.session_state.negative_keywords_raw = st.text_area(
                    "부정 키워드", value=st.session_state.negative_keywords_raw,
                    placeholder="예: 별로, 불편, 실망, 불량",
                    height=90,
                )

        positive_keywords = classify.parse_keyword_input(st.session_state.positive_keywords_raw)
        negative_keywords = classify.parse_keyword_input(st.session_state.negative_keywords_raw)

        if positive_keywords or negative_keywords:
            df = classify.classify_dataframe(df, review_column, positive_keywords, negative_keywords)

    st.write("")

    # --- 통계 카드 + 도넛 차트 ---
    if "감정분류" in df.columns:
        total = len(df)
        pos_count = int((df["감정분류"] == "긍정").sum())
        neg_count = int((df["감정분류"] == "부정").sum())
        neu_count = int((df["감정분류"] == "중립").sum())

        card_col1, card_col2, card_col3, card_col4, chart_col = st.columns([1, 1, 1, 1, 1.6])
        with card_col1:
            theme.metric_card("전체 리뷰", f"{total:,}건")
        with card_col2:
            pct = f"{pos_count/total*100:.0f}%" if total else "0%"
            theme.metric_card("긍정 리뷰", f"{pos_count:,}건", pct, "positive")
        with card_col3:
            pct = f"{neg_count/total*100:.0f}%" if total else "0%"
            theme.metric_card("부정 리뷰", f"{neg_count:,}건", pct, "negative")
        with card_col4:
            pct = f"{neu_count/total*100:.0f}%" if total else "0%"
            theme.metric_card("중립 리뷰", f"{neu_count:,}건", pct, "neutral")
        with chart_col:
            with st.container(border=True):
                st.markdown(
                    "<div class='metric-label' style='margin-bottom:0;'>감정 분류 비율</div>",
                    unsafe_allow_html=True,
                )
                st.plotly_chart(
                    sentiment_donut_chart({"긍정": pos_count, "부정": neg_count, "중립": neu_count}),
                    use_container_width=True,
                )

        st.write("")

    with st.container(border=True):
        st.subheader("📋 리뷰 데이터")

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
                group_column = "상품명" if "상품명" in df.columns else df.columns[0]
                for product_name, group in df.groupby(group_column):
                    with st.expander(f"{product_name} ({len(group)}건)"):
                        st.dataframe(group, use_container_width=True)
        else:
            st.info("키워드를 입력하면 긍정/부정/중립으로 자동 분류됩니다.")
            st.dataframe(df, use_container_width=True)

        csv = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="분류 결과 CSV로 다운로드",
            data=csv,
            file_name="reviews_classified.csv",
            mime="text/csv",
        )
else:
    with st.container(border=True):
        st.info("위에서 파일을 업로드하면 분석 결과가 여기에 표시됩니다.")
