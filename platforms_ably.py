"""
에이블리 파트너스 플랫폼 전용 데이터 수집 모듈

다른 쇼핑몰(지그재그, 쿠팡 등)을 추가할 때는 이 파일과 같은 형태로
platforms/ 폴더 안에 새 파일을 만들고, 아래와 동일한 이름의 함수들을 구현하면 됩니다:
    - login(page, user_id, password)
    - collect_reviews_by_count(page, target_count, progress_callback=None)
    - collect_reviews_by_date(page, start_date, end_date, progress_callback=None)
이렇게 형태(인터페이스)를 통일해두면, app.py 쪽 코드는 거의 수정 없이
플랫폼을 바꿔 끼울 수 있습니다.
"""

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


def login(page, user_id: str, password: str, debug_log=None):
    page.goto("https://my.a-bly.com/login/")
    page.wait_for_load_state("load")
    page.wait_for_timeout(3000)

    if debug_log is not None:
        debug_log.append(f"로그인 페이지 첫 진입 URL: {page.url}")

    try:
        email_box = page.get_by_role("textbox", name="이메일")
        email_box.click()
        email_box.fill(user_id)
        page.wait_for_timeout(500)

        password_box = page.get_by_role("textbox", name="비밀번호")
        password_box.click()
        password_box.fill(password)
        page.wait_for_timeout(500)

        # 실제로 입력이 됐는지 확인
        email_value = email_box.input_value()
        password_value = password_box.input_value()
        if debug_log is not None:
            debug_log.append(
                f"입력 확인 - 이메일 칸 글자수: {len(email_value)}, 비밀번호 칸 글자수: {len(password_value)}"
            )
    except Exception as e:
        if debug_log is not None:
            debug_log.append(f"ID/비밀번호 입력 단계에서 오류: {e}")

    try:
        page.get_by_role("button", name="로그인").click()
        if debug_log is not None:
            debug_log.append("로그인 버튼 클릭 완료")
    except Exception as e:
        if debug_log is not None:
            debug_log.append(f"로그인 버튼 클릭 오류: {e}")

    # 클라우드 환경은 네트워크가 느릴 수 있어 대기시간을 늘림
    page.wait_for_timeout(6000)

    if debug_log is not None:
        debug_log.append(f"로그인 후 URL: {page.url}")
        if "login" in page.url:
            debug_log.append("⚠️ 경고: 로그인 후에도 login 페이지에 머물러 있습니다. 로그인 실패 가능성.")

            try:
                body_text = page.locator("body").inner_text()
                debug_log.append(f"화면 텍스트 길이: {len(body_text)}자")
                debug_log.append(f"화면 텍스트(일부): {body_text[:500]!r}")
            except Exception as e:
                debug_log.append(f"화면 텍스트 읽기 실패: {e}")

            try:
                page.wait_for_timeout(2000)  # 폰트/렌더링이 완전히 끝날 시간을 추가로 확보
                screenshot_bytes = page.screenshot(full_page=True)
                debug_log.append(f"스크린샷 크기: {len(screenshot_bytes)} bytes")
                import base64
                debug_log.append(f"SCREENSHOT_BASE64:{base64.b64encode(screenshot_bytes).decode('utf-8')}")
            except Exception as e:
                debug_log.append(f"스크린샷 캡처 실패: {e}")


def _go_to_reviews_and_set_page_size(page, page_size=100, debug_log=None):
    page.goto("https://my.a-bly.com/reviews")
    page.wait_for_timeout(3000)

    if debug_log is not None:
        debug_log.append(f"리뷰 페이지 이동 후 URL: {page.url}")
        row_count_check = page.locator(".el-table__body tbody tr.el-table__row").count()
        debug_log.append(f"100개씩 보기 설정 전, 감지된 행 개수: {row_count_check}")

    try:
        page.get_by_role("textbox", name="선택").click()
        page.wait_for_timeout(500)
        page.get_by_text(f"{page_size}개씩 보기").click()
        page.wait_for_timeout(1500)
        if debug_log is not None:
            debug_log.append(f"{page_size}개씩 보기 설정 성공")
    except Exception as e:
        if debug_log is not None:
            debug_log.append(f"{page_size}개씩 보기 설정 실패: {e}")


def _apply_date_filter(page, start_date: str, end_date: str):
    """작성일시 필터에 날짜 범위를 입력하고 검색을 적용합니다.
    start_date, end_date 형식: "YYYY-MM-DD"
    """
    page.get_by_role("textbox", name="From").click()
    page.wait_for_timeout(300)

    start_box = page.get_by_role("textbox", name="시작 날짜")
    start_box.fill(start_date)
    page.wait_for_timeout(300)

    end_box = page.get_by_role("textbox", name="종료 날짜")
    end_box.click()
    end_box.fill(end_date)
    page.wait_for_timeout(300)

    page.get_by_role("button", name="확인", exact=True).click()
    page.wait_for_timeout(1000)

    # 날짜 필터 적용 후 검색 버튼을 한번 더 눌러야 실제 검색이 반영됨
    page.get_by_role("button", name="검색").click()
    page.wait_for_timeout(2000)


def _extract_rows_from_current_page(page):
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


def _go_to_next_page(page):
    try:
        next_btn = page.locator("button.btn-next")
        if next_btn.is_disabled():
            return False
        next_btn.click()
        page.wait_for_timeout(1500)
        return True
    except Exception:
        return False


def collect_reviews_by_count(page, target_count: int, progress_callback=None, debug_log=None):
    """개수를 기준으로 리뷰를 수집합니다 (최신순으로 target_count개)."""
    _go_to_reviews_and_set_page_size(page, page_size=100, debug_log=debug_log)

    all_results = []
    while len(all_results) < target_count:
        page_data = _extract_rows_from_current_page(page)
        if debug_log is not None and len(all_results) == 0:
            debug_log.append(f"첫 페이지 추출 결과: {len(page_data)}건")
        if not page_data:
            break

        all_results.extend(page_data)
        if progress_callback:
            progress_callback(min(len(all_results), target_count))

        if len(all_results) >= target_count:
            break

        has_next = _go_to_next_page(page)
        if not has_next:
            break

    return all_results[:target_count]


def collect_reviews_by_date(page, start_date: str, end_date: str, progress_callback=None, debug_log=None):
    """날짜 범위를 기준으로 해당 기간의 리뷰를 전부 수집합니다.
    start_date, end_date 형식: "YYYY-MM-DD"
    """
    _go_to_reviews_and_set_page_size(page, page_size=100, debug_log=debug_log)
    _apply_date_filter(page, start_date, end_date)

    all_results = []
    page_num = 1
    while True:
        page_data = _extract_rows_from_current_page(page)
        if not page_data:
            break

        all_results.extend(page_data)
        if progress_callback:
            progress_callback(len(all_results))

        has_next = _go_to_next_page(page)
        if not has_next:
            break
        page_num += 1

        # 안전장치: 혹시라도 무한 루프에 빠지는 것을 방지 (최대 1000페이지)
        if page_num > 1000:
            break

    return all_results
