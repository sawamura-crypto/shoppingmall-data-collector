"""
마켓인사이트 자체 로그인(인증) 모듈

현재 상태: 관리자 계정 1개만 지원 (Streamlit Secrets에 저장된 아이디/비밀번호 해시 기준)
향후 확장: 회원가입 기능을 추가할 때, 아래 get_user() 함수만
          (Secrets 조회 -> 데이터베이스 조회)로 바꿔주면 나머지 코드는 그대로 사용 가능합니다.
"""

import streamlit as st
import bcrypt


def get_user(username: str):
    """주어진 아이디에 해당하는 사용자 정보를 반환합니다.
    지금은 Secrets에 저장된 관리자 계정 1개만 확인하지만,
    추후 회원가입 기능을 붙일 때는 이 함수 내부만 DB 조회로 교체하면 됩니다.

    반환값: {"username": ..., "password_hash": ...} 또는 없으면 None
    """
    admin_username = st.secrets.get("ADMIN_USERNAME")
    admin_password_hash = st.secrets.get("ADMIN_PASSWORD_HASH")

    if admin_username and username == admin_username:
        return {"username": admin_username, "password_hash": admin_password_hash}

    return None


def verify_password(plain_password: str, password_hash: str) -> bool:
    """입력한 비밀번호가 저장된 해시값과 일치하는지 확인합니다."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


def authenticate(username: str, password: str) -> bool:
    """아이디/비밀번호가 올바른지 최종 확인합니다."""
    user = get_user(username)
    if user is None:
        return False
    return verify_password(password, user["password_hash"])


def init_auth_session_state():
    """인증 관련 세션 상태를 초기화합니다."""
    if "app_logged_in" not in st.session_state:
        st.session_state.app_logged_in = False
    if "app_username" not in st.session_state:
        st.session_state.app_username = ""


def render_login_page():
    """마켓인사이트 자체 로그인 화면을 보여줍니다. 로그인에 성공하면 True를 반환합니다."""
    init_auth_session_state()

    st.title("📊 마켓인사이트")
    st.caption("쇼핑몰 파트너스 데이터 수집·분석 도구")

    st.divider()

    _, center_col, _ = st.columns([1, 1.2, 1])
    with center_col:
        st.subheader("🔐 로그인")

        username = st.text_input("아이디")
        password = st.text_input("비밀번호", type="password")

        if st.button("로그인", type="primary", use_container_width=True):
            if not username or not password:
                st.warning("아이디와 비밀번호를 모두 입력해주세요.")
            elif authenticate(username, password):
                st.session_state.app_logged_in = True
                st.session_state.app_username = username
                st.rerun()
            else:
                st.error("아이디 또는 비밀번호가 올바르지 않습니다.")

        st.caption("※ 현재는 관리자 전용 베타 버전입니다. 회원가입은 추후 지원될 예정입니다.")

    return st.session_state.app_logged_in


def logout():
    """로그아웃 처리 (앱 자체 로그인 + 에이블리 로그인 정보까지 모두 초기화)"""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
