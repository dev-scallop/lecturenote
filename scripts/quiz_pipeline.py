# quiz_pipeline.py
# -*- coding: utf-8 -*-
import os
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


DOMAIN_RULES = {
    "it": (
        "IT 분야 퀴즈 규칙:\n"
        "- 핵심 개념 정의 문제 포함\n"
        "- 코드 출력 예측, 간단한 코드 작성, 오류 찾기 문제 혼합\n"
        "- 문제는 학생이 직접 손으로 풀어볼 수 있도록 예제 코드 또는 입력/출력 제시\n"
    ),
    "math": (
        "수학 분야 퀴즈 규칙:\n"
        "- 정의/정리 기반 문제 포함\n"
        "- 짧은 계산 문제(1~2개) 및 사고력 문제 포함\n"
        "- 증명 아이디어나 풀이 방향을 묻는 서술형 문제 포함\n"
    ),
    "biz": (
        "경영/경제 분야 퀴즈 규칙:\n"
        "- 용어 정의, 사례 기반 판단 문제, 개념 비교 문제 포함\n"
    ),
    "default": (
        "일반 분야 퀴즈 규칙:\n"
        "- 핵심 개념 문제와 예시 문제 혼합\n"
    ),
}


def _build_prompt(domain: str, chapter_text: str, captions: list, num_q: int = 6) -> str:
    domain = domain if domain in DOMAIN_RULES else "default"
    rules = DOMAIN_RULES.get(domain, DOMAIN_RULES["default"])

    # NFR: 텍스트 길이/캡션 제한
    chapter_text = (chapter_text or "")[:8000]
    captions = captions[:10]

    caption_block = "\n".join([f"- {c}" for c in captions]) if captions else "없음"

    prompt = f"""
당신은 분야별 교재용 퀴즈 출제 전문가입니다.
학생이 챕터를 학습한 뒤 스스로 점검할 수 있는 HTML 기반 퀴즈를 생성하세요.

[도메인]
{domain}

[퀴즈 규칙]
{rules}

[챕터 원문 일부]
{chapter_text}

[그림/표 캡션 목록]
{caption_block}

[출력 규칙]
- 반드시 완전한 HTML 문서로 응답하세요(<!DOCTYPE html> 포함).\n"
"- 사용 가능한 태그: <html>, <head>, <meta>, <title>, <style>, <body>, <h1>, <h2>, <p>, <section>, <details>, <summary>, <img>, <figure>, <figcaption>.\n"
"- 문제는 5개 이상 8개 이하로 작성하세요.\n"
"- 정답은 <details><summary>정답 보기</summary>...</details> 형식으로 숨기세요.\n"
"- 코드 블록 표기(예: ``` )는 사용하지 마세요. 코드가 필요하면 <pre><code>과 같은 태그 대신 inline 태그나 &lt;pre&gt;로 간단히 보여주십시오.\n"
"- 출력에는 별도의 마크다운 코드블록을 포함하지 마십시오.\n"
"- 문제 유형(단답/서술/코드/계산)을 섞어 도메인 특성에 맞게 작성하십시오.\n"
"- 문제 수는 {num_q}개로 맞추되, 도메인별 규칙을 반영하십시오.\n"
"""

    return prompt


def generate_quiz(chapter_dir: str, domain: str = "default", chapter_text: str = "", images: list = None, num_questions: int = 6) -> str:
    """Generate quiz HTML string using LLM.

    Args:
        chapter_dir: directory for context (not used to read files here)
        domain: one of math/it/biz/default
        chapter_text: raw chapter text (will be truncated to <=8000 chars)
        images: list of caption strings
        num_questions: desired number of questions (5-8 recommended)

    Returns:
        HTML string containing the quiz page
    """
    captions = images or []
    prompt = _build_prompt(domain, chapter_text, captions, num_q=min(max(5, num_questions), 8))

    # LLM 호출
    res = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {
                "role": "system",
                "content": (
                    "당신은 교육용 퀴즈를 HTML로 잘 만드는 전문가입니다. "
                    "학생 친화적이고 간결한 문제와 해설을 생성하세요."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    )

    quiz_html = res.choices[0].message.content
    # 안전 장치: 만약 LLM이 완전 HTML이 아닌 텍스트를 반환하면 간단히 감싸기
    if not quiz_html.strip().lower().startswith("<!doctype html"):
        # 최소한의 wrapper
        quiz_html = "<!DOCTYPE html>\n<html lang=\"ko\">\n<head><meta charset=\"utf-8\"><title>Quiz</title></head><body>\n" + quiz_html + "\n</body></html>"

    return quiz_html


def save_quiz(chapter_dir: str, quiz_html: str, open_browser: bool = False) -> str:
    out_path = os.path.join(chapter_dir, "quiz.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(quiz_html)

    # 옵션: 브라우저 자동 오픈 (사용자 옵션으로 호출 시)
    if open_browser:
        try:
            import webbrowser

            webbrowser.open_new_tab(f"file:///{os.path.abspath(out_path)}")
        except Exception:
            pass

    return out_path
