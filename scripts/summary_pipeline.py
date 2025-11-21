"""
summary_pipeline.py (DISABLED)

This module has been intentionally disabled per PRD. Use
`easy_explanation_pipeline.py` for generating chapter-level easy explanations.

Any attempt to call the original summary functions will raise a RuntimeError to
prevent accidental use.
"""


def summarize_chapter(*args, **kwargs):
    raise RuntimeError(
        "summary_pipeline is disabled. Use easy_explanation_pipeline.easy_explain_chapter instead."
    )


def save_summary(*args, **kwargs):
    raise RuntimeError(
        "summary_pipeline is disabled. Use easy_explanation_pipeline.save_explanation instead."
    )
"""
summary_pipeline.py (DISABLED)

This module has been intentionally disabled per PRD. Use
`easy_explanation_pipeline.py` for generating chapter-level easy explanations.

Any attempt to call the original summary functions will raise a RuntimeError to
prevent accidental use.
"""


def summarize_chapter(*args, **kwargs):
    raise RuntimeError("summary_pipeline is disabled. Use easy_explanation_pipeline.easy_explain_chapter instead.")


def save_summary(*args, **kwargs):
    raise RuntimeError("summary_pipeline is disabled. Use easy_explanation_pipeline.save_explanation instead.")
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
