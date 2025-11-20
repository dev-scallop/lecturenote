# summary_pipeline.py
# -*- coding: utf-8 -*-
import os
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ---------------------------------------------------------
# HTML 템플릿
# ---------------------------------------------------------
TEMPLATE_BASIC = """
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>요약본</title>
<style>
body { font-family: Pretendard, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
       padding: 40px; line-height: 1.6; color:#111827; }
h1, h2, h3 { margin-top: 28px; }
h1 { font-size: 28px; margin-bottom: 8px; }
h2 { font-size: 22px; }
h3 { font-size: 18px; }
p  { margin: 8px 0; }
img { max-width: 100%; margin: 15px 0; }
figure { margin: 25px 0; }
figcaption { font-size: 13px; color: #555; margin-top: 4px; }
</style>
</head>
<body>
{{content}}
</body>
</html>
"""

TEMPLATE_SLIDE = """
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>슬라이드 요약본</title>
<style>
body { font-family: Pretendard, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
       padding: 40px; background:#f3f4f6; }
.slide {
  border-radius: 12px;
  background:#ffffff;
  border: 1px solid #e5e7eb;
  padding: 32px 36px;
  margin-bottom: 36px;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.06);
}
.slide h2 { margin-top: 0; font-size: 22px; }
.slide ul { margin-top: 8px; padding-left: 20px; }
img { max-width: 100%; margin: 10px 0; }
figure { margin: 20px 0; }
figcaption { font-size: 12px; color:#6b7280; }
</style>
</head>
<body>
{{content}}
</body>
</html>
"""

TEMPLATE_BLOG = """
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>블로그 요약본</title>
<style>
body { font-family: Pretendard, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
       padding: 50px 20px; max-width: 840px; margin: auto; line-height: 1.7; color:#111827; }
h1 { font-size: 32px; margin-bottom: 20px; }
h2 { margin-top: 40px; border-left: 6px solid #2563eb; padding-left: 12px; font-size: 24px; }
h3 { margin-top: 24px; font-size: 18px; }
p  { margin: 10px 0; }
img { max-width: 100%; margin: 20px 0; border-radius: 10px; }
figure { margin: 25px 0; }
figcaption { font-size: 13px; color: #6b7280; margin-top: 4px; }
</style>
</head>
<body>
{{content}}
</body>
</html>
"""

TEMPLATE_TEXTBOOK = """
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>교재 스타일 요약</title>
<style>
body { font-family: Pretendard, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
       padding: 40px; line-height: 1.7; color:#111827; }
h1 { font-size: 30px; border-bottom: 3px solid #111827; padding-bottom: 8px; margin-bottom: 12px; }
h2 { margin-top: 30px; font-size: 22px; }
h3 { margin-top: 20px; font-size: 18px; }
p  { margin: 8px 0; }
.box {
  border: 1px solid #d1d5db; padding: 20px; background:#f9fafb; margin:20px 0; border-radius: 8px;
}
img { max-width:100%; margin:15px 0; }
figure { margin: 25px 0; }
figcaption { font-size:13px; color:#4b5563; margin-top: 4px; }
</style>
</head>
<body>
{{content}}
</body>
</html>
"""

TEMPLATE_CUSTOM = """
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>커스텀 요약</title>
<style>
body { font-family: Pretendard, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
       padding: 40px; line-height: 1.6; color:#111827; }
</style>
</head>
<body>
{{content}}
</body>
</html>
"""

TEMPLATES_BY_STYLE = {
    "basic": TEMPLATE_BASIC,
    "slide": TEMPLATE_SLIDE,
    "blog": TEMPLATE_BLOG,
    "textbook": TEMPLATE_TEXTBOOK,
    "custom": TEMPLATE_CUSTOM,
}


# ---------------------------------------------------------
# chapter.json 로드
# ---------------------------------------------------------
def load_chapter(chapter_dir: str) -> dict:
    path = os.path.join(chapter_dir, "chapter.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------
# 이미지 필터링
#   - extract_chapter.py 가 넣어준 kind(figure/table/diagram) 사용
#   - diagram_only=True 이면 figure 만 사용
# ---------------------------------------------------------
def filter_images(
    images,
    domain: str = "default",
    max_count_default: int = 10,
    diagram_only: bool = False,
):
    selected = []
    for img in images:
        kind = img.get("kind", "other")
        # figure / table / diagram(추가 도식)만 사용
        if kind not in ("figure", "table", "diagram"):
            continue
        if diagram_only and kind != "figure":
            continue

        caption = (img.get("caption") or "").strip()
        if not caption:
            continue

        selected.append(img)

    # 도식은 모두 사용하도록 별도 개수 제한은 두지 않음
    return selected


# ---------------------------------------------------------
# HTML wrapping
# ---------------------------------------------------------
def wrap_html(style: str, body: str) -> str:
    tpl = TEMPLATES_BY_STYLE.get(style, TEMPLATE_BASIC)
    return tpl.replace("{{content}}", body)


# ---------------------------------------------------------
# 도메인별 요약 규칙 문구
# ---------------------------------------------------------
def build_domain_instruction(domain: str) -> str:
    if domain == "math":
        return """■ 수학 교재 요약 규칙
- 정의/정리/공식은 별도의 문단으로 분리
- 계산과정은 핵심 단계만 간단하게 정리
- 증명은 아이디어 위주로 요약하고, 세부 계산은 생략
"""
    if domain == "it":
        return """■ IT·프로그래밍 교재 요약 규칙
- 개념 / 코드 / 예제를 분리하여 정리
- 주요 함수·메서드 이름과 역할을 명확히 남길 것
- 코드 흐름을 순서대로 설명하고, 핵심 부분만 발췌
"""
    if domain == "biz":
        return """■ 경영·경제 교재 요약 규칙
- 핵심 용어 정의 → 주요 이론 → 사례·시사점 순서로 구성
- 그림/표는 개념 간 관계, 비교 포인트를 중심으로 설명
- 불필요한 수식·숫자는 최소화하고 메시지를 강조
"""
    return """■ 일반 교재 요약 규칙
- 핵심 개념 → 주요 내용 → 예시 순서로 정리
- 문장은 짧고 명확하게, 학생이 읽기 쉽게 작성
"""


# ---------------------------------------------------------
# 메인 요약 함수
# ---------------------------------------------------------
def summarize_chapter(
    chapter_dir: str,
    mode: str = "html",
    style: str = "basic",
    use_images: str = "include",   # "include" | "no_images"
    domain: str = "default",
    diagram_only: bool = False,
    progress_callback=None,
    stop_flag=None,
    user_instruction: str = "",
) -> str:

    data = load_chapter(chapter_dir)

    # extract_chapter 에서 domain을 넣어줬으면 기본값보다 우선
    if data.get("domain") in ("math", "it", "biz"):
        if domain == "default":
            domain = data["domain"]

    # 1) 텍스트 결합 (길이 제한)
    texts = []
    for p in data.get("pages", []):
        texts.extend(p.get("text_blocks", []))
    chapter_text = "\n".join(texts)
    chapter_text = chapter_text[:15000]  # 토큰 폭주 방지

    if progress_callback:
        progress_callback(0.1)

    # 2) 이미지(그림/표) 선택
    if use_images == "no_images":
        images = []
        image_rule = "이미지는 사용하지 않고 텍스트만으로 요약합니다."
        pairs_text = "이미지 없음"
    else:
        images = filter_images(
            data.get("images", []),
            domain=domain,
            diagram_only=diagram_only,
        )

        if images:
            desc_list = []
            for i, img in enumerate(images, 1):
                cap = (img.get("caption") or "").strip()
                if not cap:
                    # 캡션이 비어 있는 도식의 경우 페이지 정보 기반 임시 설명 사용
                    page_no = img.get("page_number")
                    if page_no is not None:
                        cap = f"제목 없음 도식 (p.{page_no})"
                    else:
                        cap = "제목 없음 도식"
                local = " ".join(img.get("local_text", []))[:200]
                kind = img.get("kind", "figure")
                desc_list.append(
                    f"{i}) [{kind}] {cap}\n"
                    f"   파일: {img['file']}\n"
                    f"   주변설명: {local}"
                )
            pairs_text = "\n\n".join(desc_list)
            image_rule = (
                "아래 '그림/표' 목록은 교재에서 중요한 시각자료입니다. "
                "각 그림/표의 제목이 의미하는 바를 요약 속에서 간단히 설명해 주세요."
            )
        else:
            pairs_text = "없음"
            image_rule = "중요 그림/표가 발견되지 않았으므로 텍스트 중심으로 요약합니다."

    if progress_callback:
        progress_callback(0.2)

    # 3) 모드별 출력 규칙 (특히 HTML 모드에서 ``` 금지)
    if mode == "html":
        mode_instruction = """
HTML 웹페이지의 <body> 안에 들어갈 내용만 작성하세요.
절대 ``` 같은 코드블록 표시는 사용하지 마세요.
<html>, <head>, <body> 태그는 쓰지 말고,
<h1>, <h2>, <h3>, <p>, <ul>, <ol>, <li> 만 사용하여 구조화된 본문을 작성하세요.
"""
    elif mode == "slide":
        mode_instruction = """
슬라이드 묶음처럼 여러 섹션으로 나누어 요약하세요.
각 슬라이드는 제목(<h2>)과 핵심 bullet(<ul><li>) 목록을 포함합니다.
코드블록 표시는 사용하지 말고, 순수 HTML 태그만 사용하세요.
"""
    elif mode == "markdown":
        mode_instruction = """
마크다운 형식(#, ##, -, 1. ...)으로 요약문을 작성하세요.
"""
    elif mode == "json":
        mode_instruction = """
JSON 문자열 하나로만 응답하세요.
형식: {"title": "...", "sections": [{"heading": "...", "content": "..."} , ... ]}
"""
    else:  # "simple" 등
        mode_instruction = "일반 텍스트로 핵심만 간단히 요약하세요."

    domain_instruction = build_domain_instruction(domain)

    # 4) 프롬프트 구성
    prompt = f"""
당신은 한국어 교재 요약 전문가입니다.

{domain_instruction}

[이미지/표 사용 규칙]
{image_rule}

[중요 그림/표 목록]
{pairs_text}

[챕터 원문 일부]
{chapter_text}

[출력 규칙]
{mode_instruction}
"""

    if user_instruction:
        prompt = prompt + f"\n\n[사용자 추가 지시]\n{user_instruction}\n"

    if stop_flag and stop_flag():
        return "[중단됨]"

    # 5) LLM 호출
    res = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {
                "role": "system",
                "content": (
                    "너는 교재 내용을 쉽게 정리하는 요약 전문가이다. "
                    "특히 HTML 모드에서는 절대 ``` 같은 코드블록 마크다운을 사용하지 말고 "
                    "순수 태그 기반 본문만 생성해야 한다."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    )
    body = res.choices[0].message.content

    if progress_callback:
        progress_callback(1.0)

    # 6) HTML/SLIDE 모드일 때 실제 이미지 태그 추가
    if mode in ["html", "slide"] and use_images != "no_images" and images:
        figures_html = ["<hr><h2>중요 그림·표</h2>"]
        for img in images:
            cap = (img.get("caption") or "").strip()
            kind = img.get("kind", "figure")
            figures_html.append(
                f'<figure class="{kind}">'
                f'<img src="{img["file"]}" alt="{cap}">'
                f'<figcaption>{cap}</figcaption>'
                f'</figure>'
            )
        body = body + "\n\n" + "\n".join(figures_html)

    # 7) HTML 템플릿 감싸기
    if mode in ["html", "slide"]:
        # --- 퀴즈 자동 생성: summarize 후 동일 폴더에 quiz.html 생성 ---
        try:
            # lazy import to avoid circular issues
            from . import quiz_pipeline
        except Exception:
            try:
                import quiz_pipeline
            except Exception:
                quiz_pipeline = None

        if quiz_pipeline is not None:
            try:
                # captions: images 리스트에서 캡션만 추출, 최대 10개
                captions = [ (img.get('caption') or '').strip() for img in images ] if images else []
                captions = [c for c in captions if c][:10]
                # chapter_text는 summarize_chapter에서 이미 생성한 변수
                quiz_html = quiz_pipeline.generate_quiz(
                    chapter_dir=chapter_dir,
                    domain=domain,
                    chapter_text=chapter_text[:8000],
                    images=captions,
                    num_questions=6,
                )
                quiz_pipeline.save_quiz(chapter_dir, quiz_html)
            except Exception:
                # 퀴즈 생성 실패해도 요약은 반환되어야 함
                pass

        return wrap_html(style, body)

    return body


# ---------------------------------------------------------
# 결과 저장
# ---------------------------------------------------------
def save_summary(chapter_dir: str, text: str, mode: str = "html") -> str:
    ext = {
        "html": ".html",
        "slide": ".html",
        "markdown": ".md",
        "json": ".json",
        "simple": ".txt",
    }.get(mode, ".txt")

    out_path = os.path.join(chapter_dir, f"summary{ext}")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)
    return out_path
