"""
마켓인사이트 ERP 스타일 테마

이 파일은 st.markdown(unsafe_allow_html=True)로 주입할 커스텀 CSS를 정의합니다.
색상/레이아웃을 한 곳에서 관리하기 위해 별도 파일로 분리했습니다.
"""

COLORS = {
    "bg": "#F5F7FB",
    "card": "#FFFFFF",
    "border": "#E7EBF3",
    "primary": "#3B6BF2",
    "primary_dark": "#2952CC",
    "text": "#1E2A3D",
    "text_muted": "#7C8AA0",
    "positive": "#16A34A",
    "positive_bg": "#E9F8EF",
    "negative": "#E14B4B",
    "negative_bg": "#FCEAEA",
    "neutral": "#94A3B8",
    "neutral_bg": "#F1F3F8",
}

CSS = f"""
<style>
    .stApp {{
        background-color: {COLORS['bg']};
    }}

    /* 사이드바 */
    section[data-testid="stSidebar"] {{
        background-color: {COLORS['card']};
        border-right: 1px solid {COLORS['border']};
    }}

    /* 본문 폰트 색상 */
    h1, h2, h3, h4, p, span, label {{
        color: {COLORS['text']};
    }}

    /* 카드 컨테이너 (st.container(border=True)에 적용됨) */
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background-color: {COLORS['card']};
        border-radius: 16px;
        border: 1px solid {COLORS['border']};
        box-shadow: 0 1px 3px rgba(30, 42, 61, 0.04);
    }}

    /* 기본 버튼 */
    .stButton button {{
        border-radius: 10px;
        font-weight: 600;
    }}
    .stButton button[kind="primary"] {{
        background-color: {COLORS['primary']};
        border-color: {COLORS['primary']};
    }}
    .stButton button[kind="primary"]:hover {{
        background-color: {COLORS['primary_dark']};
        border-color: {COLORS['primary_dark']};
    }}

    /* 입력창 모서리 */
    .stTextInput input, .stTextArea textarea, .stNumberInput input {{
        border-radius: 10px;
    }}

    /* 탭 디자인 */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 4px;
    }}
    .stTabs [data-baseweb="tab"] {{
        border-radius: 10px 10px 0 0;
        padding: 8px 18px;
    }}

    /* 통계 카드 */
    .metric-card {{
        background-color: {COLORS['card']};
        border: 1px solid {COLORS['border']};
        border-radius: 16px;
        padding: 20px 22px;
        box-shadow: 0 1px 3px rgba(30, 42, 61, 0.04);
    }}
    .metric-label {{
        font-size: 13px;
        color: {COLORS['text_muted']};
        font-weight: 600;
        margin-bottom: 6px;
    }}
    .metric-value {{
        font-size: 30px;
        font-weight: 700;
        color: {COLORS['text']};
        line-height: 1.2;
    }}
    .metric-sub {{
        font-size: 12px;
        margin-top: 6px;
        font-weight: 600;
        display: inline-block;
        padding: 2px 8px;
        border-radius: 6px;
    }}
    .metric-sub.positive {{ color: {COLORS['positive']}; background-color: {COLORS['positive_bg']}; }}
    .metric-sub.negative {{ color: {COLORS['negative']}; background-color: {COLORS['negative_bg']}; }}
    .metric-sub.neutral {{ color: {COLORS['neutral']}; background-color: {COLORS['neutral_bg']}; }}

    /* 사이드바 로고 영역 */
    .sidebar-logo {{
        font-size: 20px;
        font-weight: 800;
        color: {COLORS['text']};
        padding: 4px 0 0 0;
    }}
    .sidebar-user {{
        font-size: 13px;
        color: {COLORS['text_muted']};
    }}
</style>
"""


def inject():
    import streamlit as st
    st.markdown(CSS, unsafe_allow_html=True)


def metric_card(label, value, sub_text=None, sub_type="neutral"):
    """ERP 대시보드 스타일의 통계 카드를 렌더링합니다."""
    import streamlit as st
    sub_html = f'<span class="metric-sub {sub_type}">{sub_text}</span>' if sub_text else ""
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
