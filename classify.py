"""
리뷰 감정(긍정/부정/중립) 분류 모듈

규칙:
- 리뷰 내용에 긍정 키워드가 하나라도 포함되고, 부정 키워드는 없으면 -> 긍정
- 부정 키워드가 하나라도 포함되고, 긍정 키워드는 없으면 -> 부정
- 둘 다 포함되거나, 둘 다 없으면 -> 중립(회색)
"""


def classify_review(text, positive_keywords: list, negative_keywords: list) -> str:
    """리뷰 텍스트 하나를 '긍정' / '부정' / '중립' 중 하나로 분류합니다."""
    # 리뷰가 빈 칸인 경우 pandas가 NaN(float)으로 읽어들이는 경우가 있어서,
    # 문자열이 아니면 빈 문자열로 처리합니다.
    if not isinstance(text, str) or not text:
        return "중립"

    has_positive = any(keyword.strip() in text for keyword in positive_keywords if keyword.strip())
    has_negative = any(keyword.strip() in text for keyword in negative_keywords if keyword.strip())

    if has_positive and not has_negative:
        return "긍정"
    elif has_negative and not has_positive:
        return "부정"
    else:
        return "중립"


def classify_dataframe(df, review_column: str, positive_keywords: list, negative_keywords: list):
    """데이터프레임의 리뷰 칸을 기준으로 '감정분류' 컬럼을 추가합니다."""
    df = df.copy()
    df["감정분류"] = df[review_column].apply(
        lambda text: classify_review(text, positive_keywords, negative_keywords)
    )
    return df


def parse_keyword_input(raw_text: str) -> list:
    """사용자가 입력한 키워드 문자열(쉼표 또는 줄바꿈으로 구분)을 리스트로 변환합니다."""
    if not raw_text:
        return []
    # 쉼표와 줄바꿈 둘 다 구분자로 허용
    parts = raw_text.replace("\n", ",").split(",")
    return [p.strip() for p in parts if p.strip()]
