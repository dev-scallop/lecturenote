# easy_explanation_pipeline.py
# -*- coding: utf-8 -*-
"""
Easy Explanation Pipeline

Creates a chapter-level "Easy Explanation Guide" HTML file per PRD.

Important constraints implemented in the system prompt:
 - Do NOT invent or hallucinate concepts, formulas, code, or graphs
 - All explanations must be grounded in the provided chapter text and image captions
 - The user's additional instructions are appended at the end of the prompt

This module exposes:
 - easy_explain_chapter(chapter_dir, ...)
 - save_explanation(chapter_dir, html)
 - load_chapter(chapter_dir)

The produced HTML strictly follows the structure required by the PRD.
"""
import os
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def load_chapter(chapter_dir: str) -> dict:
    path = os.path.join(chapter_dir, "chapter.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def filter_images(images, diagram_only: bool = False):
    # Keep only figure/table/diagram with non-empty caption
    selected = []
    for img in images:
        kind = img.get("kind", "other")
        if kind not in ("figure", "table", "diagram"):
            continue
        if diagram_only and kind != "figure":
            continue
        caption = (img.get("caption") or "").strip()
        if not caption:
            continue
        selected.append(img)
    return selected


def build_domain_instruction(domain: str) -> str:
    # Strongly different explanation styles per domain as required
    if domain == "math":
        return (
            "[도메인 규칙 - 수학]\n"
            "- 정의/정리/공식은 명확한 문장으로 분리하여 쉽고 직관적으로 풀이하세요.\n"
            "- 계산 과정은 핵심 단계만 남기고, 가능한 한 그림(도식) 중심으로 개념적 설명을 제공하세요.\n"
            "- 절대 원문에 없는 정리/공식/증명은 생성하지 마세요.\n"
        )
    if domain == "it":
        return (
            "[도메인 규칙 - IT/프로그래밍]\n"
            "- 개념 설명은 비유·단계로 풀고, 코드나 알고리즘을 언급할 때는 원문 근거만 사용하세요.\n"
            "- 함수/구조의 역할을 그림·순서도 형태로 쉽게 설명하세요.\n"
            "- 원문에 없는 코드 예시는 절대 추가하지 마세요.\n"
        )
    if domain == "biz":
        return (
            "[도메인 규칙 - 경영/경제]\n"
            "- 주요 개념은 사례·비유와 함께 쉽게 설명하고, 표·도식은 비교 포인트 중심으로 해설하세요.\n"
            "- 수치나 그래프는 원문에 있는 내용만 언급하세요.\n"
        )
    return (
        "[도메인 규칙 - 일반]\n"
        "- 핵심 개념을 먼저 쉬운 문장으로 설명하고, 필요한 경우 도식·표를 참조하여 이해를 돕는 방식을 사용하세요.\n"
        "- 원문에 없는 개념이나 예시는 생성하지 마세요.\n"
    )


def build_system_message() -> str:
    # Enforce no-hallucination and strict grounding in the original text
    return (
        "너는 '쉬운 해설서(Easy Explanation Guide)'를 작성하는 전문가이다.\n"
        "아래 지침을 반드시 지켜라:\n"
        "1) 절대로 원문(chapter.json의 text, 캡션, 주변설명)에 나오지 않는 개념·정의·공식·코드·그래프·숫자를 생성하지 마라.\n"
        "2) 모든 설명은 반드시 원문 근거에 기반해야 하며, 필요한 경우 원문 위치(페이지 번호)를 참조하라.\n"
        "3) 사용자가 추가한 지시문(user_instruction)은 프롬프트의 마지막에만 반영하라(우선순위: 시스템 메시지 > 본문 지시 > 사용자 지시).\n"
        "4) HTML 구조는 엄격히 PRD에 명시된 태그와 순서를 따라야 한다.\n"
        "5) 간결하고 학생 친화적인 한국어로 작성하되, 사실을 왜곡하지 마라.\n"
    )


def build_prompt(chapter_text: str, images_desc: str, domain_instruction: str, user_instruction: str) -> str:
    prompt = []
    prompt.append("챕터 원문(일부):\n" + chapter_text[:15000])
    prompt.append("\n도메인별 지침:\n" + domain_instruction)
    prompt.append("\n이미지/표 정보(캡션 등):\n" + images_desc)
    prompt.append(
        "\n출력 제약:\n- 결과는 완성된 HTML 문서의 <body> 안에 들어갈 본문만 작성하지 말고, PRD에 맞는 전체 HTML 문서를 생성하라.\n- 절대 원문에 없는 개념/공식/코드/그래프/숫자를 추가하지 마라.\n"
    )
    if user_instruction:
        prompt.append("\n사용자 추가 지시(아래에만 반영):\n" + user_instruction)
    return "\n\n".join(prompt)


def render_prd_html(title: str, sections: dict, figures_html: str, appendix_html: str) -> str:
    # Construct HTML exactly as PRD requested but with modern design
    
    css = """
    <style>
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
        
        :root {
            --primary-color: #2563eb;
            --bg-color: #f8fafc;
            --card-bg: #ffffff;
            --text-main: #1e293b;
            --text-sub: #475569;
            --border-color: #e2e8f0;
        }

        body {
            font-family: Pretendard, -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            line-height: 1.75;
            margin: 0;
            padding: 40px 20px;
        }

        .container {
            max_width: 800px;
            margin: 0 auto;
            background: var(--card-bg);
            padding: 60px;
            border-radius: 16px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }

        h1 {
            font-size: 2.5rem;
            font-weight: 800;
            color: #0f172a;
            margin-bottom: 2rem;
            padding-bottom: 1rem;
            border-bottom: 2px solid var(--border-color);
            letter-spacing: -0.025em;
        }

        h2 {
            font-size: 1.75rem;
            font-weight: 700;
            color: #1e293b;
            margin-top: 3rem;
            margin-bottom: 1.5rem;
            display: flex;
            align-items: center;
        }
        
        h2::before {
            content: '';
            display: inline-block;
            width: 6px;
            height: 28px;
            background-color: var(--primary-color);
            margin-right: 12px;
            border-radius: 3px;
        }

        p {
            margin-bottom: 1.25rem;
            font-size: 1.1rem;
            color: var(--text-sub);
        }

        ul {
            padding-left: 1.5rem;
            margin-bottom: 1.5rem;
        }

        li {
            margin-bottom: 0.75rem;
            color: var(--text-sub);
            font-size: 1.1rem;
        }

        figure {
            margin: 2.5rem 0;
            background: #f1f5f9;
            padding: 20px;
            border-radius: 12px;
            text-align: center;
        }

        img {
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }

        figcaption {
            margin-top: 12px;
            font-size: 0.95rem;
            color: #64748b;
            font-weight: 500;
        }

        hr {
            border: 0;
            height: 1px;
            background: var(--border-color);
            margin: 4rem 0;
        }

        .badge {
            display: inline-block;
            padding: 4px 12px;
            background-color: #dbeafe;
            color: #1e40af;
            border-radius: 9999px;
            font-size: 0.875rem;
            font-weight: 600;
            margin-bottom: 1rem;
        }

        @media (max-width: 768px) {
            .container {
                padding: 30px 20px;
            }
            h1 {
                font-size: 2rem;
            }
            h2 {
                font-size: 1.5rem;
            }
        }
    </style>
    """

    body = []
    body.append(f'<div class="container">')
    body.append(f'<span class="badge">Easy Explanation Guide</span>')
    body.append(f"<h1>{title}</h1>")
    
    # 1. 핵심 개념
    body.append("<h2>1. 핵심 개념 쉽게 설명하기</h2>")
    body.append(f"<p>{sections.get('core_concepts','').strip()}</p>")

    # 2. 중요한 도식·표 해설
    body.append("<h2>2. 중요한 도식·표 해설</h2>")
    body.append(figures_html)

    # For each figure, include a short paragraph if provided in sections
    fig_pars = sections.get('figure_explanations', [])
    for p in fig_pars:
        body.append(f"<p>{p}</p>")

    # 3. 기초 지식 보충
    body.append("<h2>3. 기초 지식 보충</h2>")
    body.append(f"<p>{sections.get('background','').strip()}</p>")

    # 4. 예시·비유로 다시 설명
    body.append("<h2>4. 예시·비유로 다시 설명</h2>")
    body.append(f"<p>{sections.get('examples','').strip()}</p>")

    # 5. 반드시 기억해야 하는 포인트
    body.append("<h2>5. 반드시 기억해야 하는 포인트</h2>")
    bullets = sections.get('takeaways', [])
    if bullets:
        body.append("<ul>")
        for b in bullets:
            body.append(f"<li>{b}</li>")
        body.append("</ul>")
    else:
        body.append("<p></p>")

    body.append("<hr>")
    # Appendix
    body.append("<h2>부록: 전체 도식 해설</h2>")
    body.append(appendix_html)
    
    body.append("</div>") # End container

    html = ["<!DOCTYPE html>", "<html>", "<head>", '<meta charset="utf-8">', '<meta name="viewport" content="width=device-width, initial-scale=1.0">', f"<title>{title} - 쉬운 해설서</title>", css, "</head>", "<body>", "\n".join(body), "</body>", "</html>"]
    return "\n".join(html)


def easy_explain_chapter(
    chapter_dir: str,
    domain: str = "default",
    use_images: str = "include",
    diagram_only: bool = False,
    progress_callback=None,
    stop_flag=None,
    user_instruction: str = "",
) -> str:
    """
    Generate the Easy Explanation Guide HTML for a chapter and return it.
    """
    data = load_chapter(chapter_dir)

    # domain override from chapter.json if present
    if data.get("domain") in ("math", "it", "biz") and domain == "default":
        domain = data["domain"]

    # collect text
    texts = []
    for p in data.get("pages", []):
        texts.extend(p.get("text_blocks", []))
    chapter_text = "\n".join(texts)[:20000]

    if progress_callback:
        progress_callback(0.1)

    # images
    if use_images == "no_images":
        images = []
    else:
        images = filter_images(data.get("images", []), diagram_only=diagram_only)

    # build image description text for prompt
    img_descs = []
    for i, img in enumerate(images, start=1):
        cap = (img.get("caption") or "").strip()
        loc = " ".join(img.get("local_text", []) or [])[:200]
        page_no = img.get("page_number")
        page_ref = f"(p.{page_no})" if page_no is not None else ""
        img_descs.append(f"{i}) [{img.get('kind','figure')}] {cap} {page_ref}\n주변설명: {loc}\n파일: {img.get('file')}")
    images_desc = "\n\n".join(img_descs) if img_descs else "없음"

    if progress_callback:
        progress_callback(0.2)

    domain_instruction = build_domain_instruction(domain)
    system_message = build_system_message()
    prompt_text = build_prompt(chapter_text, images_desc, domain_instruction, user_instruction)

    if stop_flag and stop_flag():
        return "[중단됨]"

    # call LLM
    res = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt_text},
        ],
    )

    content = res.choices[0].message.content

    if progress_callback:
        progress_callback(0.8)

    # We expect the LLM to return structured text pieces that we must map to PRD sections.
    # To keep the code robust even if LLM returns full HTML, attempt to extract plain pieces by
    # asking the model to honor the PRD, but fall back to wrapping the whole content into
    # the 'core_concepts' section if parsing is not straightforward.

    # Naive split: look for headers that the model should produce. If not found, place content as core.
    sections = {
        "core_concepts": "",
        "figure_explanations": [],
        "background": "",
        "examples": "",
        "takeaways": [],
    }

    # Try simple heuristics based on known Korean headings
    try:
        txt = content
        # Try to find the five sections by heading markers
        import re

        def extract_between(h1, h2, text):
            p = re.search(re.escape(h1) + r"(.*?)" + re.escape(h2), text, flags=re.S)
            return p.group(1).strip() if p else None

        core = extract_between("1.", "2.", txt) or extract_between("1)", "2)", txt)
        if core:
            sections["core_concepts"] = core
        else:
            sections["core_concepts"] = txt[:4000]

        figs = extract_between("2.", "3.", txt)
        if figs:
            # split figure paragraphs by double newlines
            for part in [p.strip() for p in figs.split('\n\n') if p.strip()]:
                sections["figure_explanations"].append(part)

        bg = extract_between("3.", "4.", txt)
        if bg:
            sections["background"] = bg

        ex = extract_between("4.", "5.", txt)
        if ex:
            sections["examples"] = ex

        take = None
        m = re.search(r"5\.(.*)부록", txt, flags=re.S)
        if m:
            take = m.group(1)
        else:
            # try 5. ... until end
            take = txt.split("5.", 1)[-1] if "5." in txt else None
        if take:
            # extract bullet lines
            bullets = [l.strip().lstrip("-•") for l in take.splitlines() if l.strip()][:8]
            sections["takeaways"] = bullets
    except Exception:
        # Fallback - place all content in core_concepts
        sections["core_concepts"] = content

    # Build figures HTML for section 2 and appendix
    figures_html_parts = []
    appendix_parts = []
    for img in images:
        cap = (img.get("caption") or "").strip()
        kind = img.get("kind", "figure")
        img_tag = f'<figure class="{kind}">\n  <img src="{img.get("file")}" alt="{cap}">\n  <figcaption>{cap}</figcaption>\n</figure>'
        figures_html_parts.append(img_tag)
        appendix_parts.append(img_tag)

    figures_html = "\n".join(figures_html_parts) if figures_html_parts else "<p>중요한 도식·표가 발견되지 않았습니다.</p>"
    appendix_html = "\n".join(appendix_parts) if appendix_parts else "<p>도식·표가 없습니다.</p>"

    # Title from chapter metadata
    title = data.get("title") or os.path.basename(chapter_dir)

    html = render_prd_html(title, sections, figures_html, appendix_html)

    if progress_callback:
        progress_callback(1.0)

    return html


def save_explanation(chapter_dir: str, html: str) -> str:
    out_path = os.path.join(chapter_dir, "easy_explanation.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return out_path
