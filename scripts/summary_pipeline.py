# summary_pipeline.py
# -*- coding: utf-8 -*-
import os
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ---------------------------------------------------------
# HTML 템플릿 (기존 그대로)
# ---------------------------------------------------------
TEMPLATE_BASIC = """
<html>
<head>
<meta charset="utf-8">
<title>Chapter Summary</title>
<style>
body {
  font-family: "Pretendard","Noto Sans KR",system-ui;
  line-height: 1.8;
  max-width: 820px;
  margin: 40px auto;
  padding: 0 20px 40px;
  color: #111827;
  background: #ffffff;
}
h1,h2 {
  margin-top: 30px;
  margin-bottom: 12px;
}
p { margin: 6px 0; }
img {
  max-width: 95%;
  margin: 20px 0;
  border-radius: 8px;
}
.caption {
  color:#6b7280;
  font-size:14px;
  margin-top:-10px;
  margin-bottom:22px;
}
</style>
</head>
<body>
{{content}}
</body>
</html>
"""

TEMPLATE_SLIDE = """
<html>
<head>
<meta charset="utf-8">
<title>Chapter Slide Summary</title>
<style>
body {
  font-family: "Pretendard","Noto Sans KR",system-ui;
  background:#f3f4f6;
  padding:40px;
}
section {
  background:#ffffff;
  border-radius:14px;
  padding:24px 28px;
  margin-bottom:28px;
  box-shadow:0 2px 8px rgba(15,23,42,0.08);
}
h1 { font-size:30px; margin-bottom:18px; }
h2 { font-size:24px; margin-bottom:12px; }
p  { font-size:18px; line-height:1.7; margin:6px 0; }
li { margin-bottom:4px; }
img {
  max-width:100%;
  margin:16px 0;
  border-radius:10px;
}
.caption {
  font-size:14px;
  color:#6b7280;
}
</style>
</head>
<body>
{{content}}
</body>
</html>
"""

TEMPLATE_BLOG = """
<html>
<head>
<meta charset="utf-8">
<title>Chapter Blog Summary</title>
<style>
body {
  font-family: "Pretendard","Noto Sans KR",system-ui;
  background:#ffffff;
  color:#111827;
  max-width:860px;
  margin:40px auto;
  padding:0 20px 40px;
  line-height:1.9;
}
h1,h2 {
  font-weight:600;
  margin-top:32px;
  margin-bottom:10px;
  border-left:4px solid #2563eb;
  padding-left:10px;
}
a { color:#2563eb; }
img {
  max-width:100%;
  margin:22px 0 10px 0;
  border-radius:10px;
  box-shadow:0 2px 10px rgba(15,23,42,0.15);
}
.caption {
  font-size:13px;
  color:#6b7280;
  text-align:center;
  margin-bottom:24px;
}
code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono","Courier New", monospace;
  background:#f3f4f6;
  padding:2px 4px;
  border-radius:4px;
}
pre {
  background:#020617;
  color:#e5e7eb;
  padding:14px 16px;
  border-radius:8px;
  overflow-x:auto;
}
</style>
</head>
<body>
{{content}}
</body>
</html>
"""

TEMPLATE_TEXTBOOK = """
<html>
<head>
<meta charset="utf-8">
<title>Chapter Textbook Style</title>
<style>
body {
  font-family: "Pretendard","Noto Sans KR",system-ui;
  background:#f9fafb;
  color:#111827;
  max-width:900px;
  margin:30px auto;
  padding:0 24px 40px;
  line-height:1.85;
}
.header {
  background:#1f2937;
  color:#f9fafb;
  padding:16px 20px;
  border-radius:10px;
  margin-bottom:24px;
}
.header h1 {
  margin:0;
  font-size:24px;
}
h2 {
  margin-top:28px;
  margin-bottom:8px;
  padding:8px 10px;
  background:#e5e7eb;
  border-radius:6px;
  border-left:4px solid #2563eb;
}
hr {
  border:none;
  border-top:1px solid #d1d5db;
  margin:24px 0;
}
img {
  max-width:100%;
  margin:18px 0 10px 0;
  border-radius:8px;
}
.caption {
  font-size:13px;
  color:#4b5563;
  text-align:center;
  margin-bottom:22px;
}
p { margin:6px 0; }
</style>
</head>
<body>
{{content}}
</body>
</html>
"""

TEMPLATE_CUSTOM = """
<html>
<head>
<meta charset="utf-8">
<title>Chapter Custom Style</title>
<!-- 필요하면 여기 CSS를 직접 수정해서 브랜드 스타일 적용 -->
<style>
body {
  font-family: "Pretendard","Noto Sans KR",system-ui;
  line-height: 1.8;
  max-width: 820px;
  margin: 40px auto;
  padding: 0 20px 40px;
}
img { max-width: 100%; margin: 16px 0; }
.caption { font-size: 14px; color: #666; }
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
def load_chapter(chapter_dir):
    path = os.path.join(chapter_dir, "chapter.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------
# 이미지 필터링 – 분야별로 약간 차등
# ---------------------------------------------------------
def filter_images(images, domain="default",
                  max_count_default=3, min_size_default=80):
    """
    분야별로 max_count / min_size를 조정한다.
    """
    if domain == "math":
        max_count = 4
        min_size = 60
    elif domain == "it":
        max_count = 2
        min_size = 120
    elif domain == "biz":
        max_count = 3
        min_size = 140
    else:
        max_count = max_count_default
        min_size = min_size_default

    usable = []
    for img in images:
        bbox = img["bbox"]
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        if w < min_size or h < min_size:
            continue
        if not img["local_text"]:
            continue
        usable.append((w * h, img))

    usable.sort(key=lambda x: x[0], reverse=True)
    usable = [x[1] for x in usable[:max_count]]
    return usable


# ---------------------------------------------------------
# HTML 래핑
# ---------------------------------------------------------
def wrap_html(style: str, body: str) -> str:
    tpl = TEMPLATES_BY_STYLE.get(style, TEMPLATE_BASIC)
    return tpl.replace("{{content}}", body)


# ---------------------------------------------------------
# 분야별 요약 지침 생성
#   domain: "default" / "math" / "it" / "biz"
# ---------------------------------------------------------
def build_domain_instruction(domain: str) -> str:
    if domain == "math":
        return """
이 챕터는 수학/수리 내용입니다.

- 정의, 정리, 조건, 예제를 분리해서 설명해 주세요.
- 중요한 수식은 그대로 남기되, 말로도 쉽게 풀이해 주세요.
- 그래프나 그림은 '어떤 관계를 보여주는지' 한두 문장으로 요약해 주세요.
- 단계별로 왜 그런 결론이 나오는지 직관적으로 풀어주세요.
"""
    elif domain == "it":
        return """
이 챕터는 IT/프로그래밍 내용입니다.

- 핵심 개념(예: 반복문, 조건문, 함수)을 먼저 간단히 설명해 주세요.
- 코드 블록이 무엇을 하는지, 입력과 출력이 무엇인지 자연어로 풀어주세요.
- 실제 예시(예: 1부터 10까지 합 구하기)를 들어 설명해 주세요.
- 초보자가 '왜 이렇게 코드를 짜야 하는지' 이해할 수 있도록 설명해 주세요.
"""
    elif domain == "biz":
        return """
이 챕터는 경영/경제/회계 내용입니다.

- 표와 숫자에서 드러나는 핵심 차이(더 크다/작다, 증가/감소)를 정리해 주세요.
- 개념(예: 복식부기, 저가법)의 정의를 한 문장으로 설명하고, 바로 생활/회사 예시를 들어 주세요.
- 그래프나 그림은 '거래 흐름'이나 '관계 구조'를 한두 문장으로 요약해 주세요.
- 너무 세부적인 숫자 나열보다는, 의사결정에 중요한 포인트 위주로 정리해 주세요.
"""
    else:
        return """
분야와 관계없이, 중학생도 이해할 수 있을 정도로 쉽게 풀어 설명해 주세요.
- 핵심 개념 → 쉬운 예시 → 핵심 정리 순서로 구성하면 좋습니다.
"""


# ---------------------------------------------------------
# 요약 생성
#   mode : "html" / "slide" / "markdown" / "json" / "simple"
#   style: "basic" / "slide" / "blog" / "textbook" / "custom"
#   use_images: "include" / "no_images"
#   domain: "default" / "math" / "it" / "biz"
# ---------------------------------------------------------
def summarize_chapter(
    chapter_dir,
    mode="html",
    style="basic",
    use_images="include",
    domain="default",
    progress_callback=None,
    stop_flag=None
):
    data = load_chapter(chapter_dir)

    # chapter.json에 domain이 있으면 우선 사용
    ch_domain = data.get("domain")
    if ch_domain in ("default", "math", "it", "biz"):
        domain = ch_domain if domain == "default" else domain

    # 전체 텍스트 결합(너무 길면 자름)
    texts = []
    for p in data.get("pages", []):
        texts.extend(p.get("text_blocks", []))
    chapter_text = "\n".join(texts)
    if len(chapter_text) > 15000:
        chapter_text = chapter_text[:15000]

    if progress_callback:
        progress_callback(0.1)

    # 이미지 사용 여부에 따른 처리
    if use_images == "no_images":
        images = []
    else:
        images = filter_images(data.get("images", []), domain=domain)

    if progress_callback:
        progress_callback(0.2)

    # 이미지-텍스트 페어 설명
    if use_images == "no_images":
        pairs_text = "이미지를 사용하지 않습니다."
        image_rule = """
이미지를 삽입하지 마세요.
<img>, <div class="caption"> 같은 태그도 사용하지 마세요.
"""
    else:
        pairs_desc = []
        for idx, img in enumerate(images, 1):
            fname = img["file"]
            local_txt = " ".join(img["local_text"])[:200]
            pairs_desc.append(
                f"{idx}) 파일명: {fname}\n   설명: {local_txt}"
            )
        pairs_text = "\n\n".join(pairs_desc) if pairs_desc else "없음"
        image_rule = """
이미지가 도움이 되는 경우에만 <img src="파일명"> 과
<div class="caption">간단한 설명</div> 을 사용해서 넣어 주세요.
"""

    # -----------------------------------------------------
    # 모드별 출력 규칙
    # -----------------------------------------------------
    if mode == "html":
        mode_instruction = """
출력 형식:
- <h2>로 섹션 제목
- <p>로 쉬운 설명
- <html>, <body>는 쓰지 말고, <body> 안에 들어갈 내용만 작성
"""
    elif mode == "slide":
        mode_instruction = """
출력 형식:
- 각 슬라이드를 <section>으로 나누어 작성
- <h2> 슬라이드 제목
- <ul><li> 로 핵심 포인트 3~5개
- <html>, <body>는 쓰지 말고, <body> 안에 들어갈 내용만 작성
"""
    elif mode == "markdown":
        mode_instruction = """
출력 형식:
- Markdown 문서로 작성
- #, ##, ### 제목 사용
- 본문은 자연스러운 문장
- 이미지를 쓸 경우: ![설명](파일명)
"""
    elif mode == "json":
        mode_instruction = """
출력 형식:
- JSON 문자열만 출력
- 다른 설명 문장 쓰지 말 것
예시 구조:
{
  "title": "챕터 제목",
  "sections": [
    {
      "name": "섹션 이름",
      "summary": "쉬운 설명",
      "images": [
        {"file": "파일명.png", "caption": "간단한 설명"}
      ]
    }
  ]
}
"""
    else:  # simple
        mode_instruction = """
출력 형식:
- 이 챕터를 3줄로만 요약
- 각 줄은 한 문장
- 쉬운 단어 사용
"""

    domain_instruction = build_domain_instruction(domain)

    prompt = f"""
당신은 프로그래밍·수학·경영경제 등 다양한 교재를
중학생도 이해할 수 있는 말로 설명해 주는 한국어 튜터입니다.

아래 텍스트는 한 챕터의 원문이고,
그 아래는 PDF에서 추출한 이미지-텍스트 페어 정보입니다.

{domain_instruction}

{image_rule}

[이미지-텍스트 페어]
{pairs_text}

[챕터 원문 텍스트(일부)]
{chapter_text}

{mode_instruction}
"""

    if stop_flag and stop_flag():
        return "[중단됨]"

    res = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {
                "role": "system",
                "content": "너는 교재 내용을 아주 쉽게 풀어 설명하는 한국어 튜터이자 요약 생성기다."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    body = res.choices[0].message.content

    if progress_callback:
        progress_callback(1.0)

    # 모드별 최종 텍스트 구성
    if mode in ["html", "slide"]:
        return wrap_html(style, body)
    else:
        return body


# ---------------------------------------------------------
# 저장: 모드별 확장자 선택
# ---------------------------------------------------------
def save_summary(chapter_dir, text, mode="html"):
    ext_map = {
        "html": ".html",
        "slide": ".html",
        "markdown": ".md",
        "json": ".json",
        "simple": ".txt",
    }
    ext = ext_map.get(mode, ".txt")
    out_path = os.path.join(chapter_dir, f"summary{ext}")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)
    return out_path
