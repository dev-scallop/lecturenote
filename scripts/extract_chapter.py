# extract_chapter.py
# -*- coding: utf-8 -*-
import fitz  # PyMuPDF
import os
import json


# ---------------------------------------------------------
# (A) PDF 목차(TOC) 기반 챕터 분석 – 공통 엔진
# ---------------------------------------------------------
def find_chapter_starts(doc):
    """
    PDF TOC(목차) 기반으로 챕터 리스트를 만든다.
    TOC 구조: [level, title, page_number]
    level == 1 : 최상위 챕터
    """
    toc = doc.get_toc()
    if not toc:
        raise RuntimeError("PDF에 TOC(목차)가 없습니다.")

    lvl1 = [t for t in toc if t[0] == 1]
    chapters = []

    for i, (level, title, page_num) in enumerate(lvl1):
        start = page_num - 1  # PyMuPDF page index (0-based)

        if i == len(lvl1) - 1:
            end = doc.page_count
        else:
            next_start = lvl1[i + 1][2] - 1
            end = next_start

        chapters.append({
            "index": i + 1,
            "title": title,
            "start": start,
            "end": end
        })

    return chapters


# ---------------------------------------------------------
# (B) 기본 페이지 추출 엔진 (default)
# ---------------------------------------------------------
def _extract_page_blocks_default(page, chapter_idx, page_abs_index, out_dir,
                                 max_local_blocks=3):
    """
    기본 엔진:
      - 텍스트 블록
      - 이미지 블록 (PNG 저장)
      - 이미지 아래 텍스트 1~3개 local_text 로 묶기
    """
    page_dict = page.get_text("dict")
    blocks = page_dict["blocks"]

    text_blocks = []
    image_blocks = []

    img_counter = 0
    page_texts = []

    for idx, b in enumerate(blocks):
        btype = b.get("type", 0)
        bbox = b.get("bbox", [0, 0, 0, 0])

        # 텍스트
        if btype == 0:
            text = ""
            for line in b.get("lines", []):
                for span in line.get("spans", []):
                    text += span.get("text", "")
                text += "\n"
            text = text.strip()
            if text:
                text_blocks.append({
                    "index": idx,
                    "text": text,
                    "bbox": bbox
                })
                page_texts.append(text)

        # 이미지
        elif btype == 1:
            img_counter += 1
            image_blocks.append({
                "index": idx,
                "bbox": bbox,
                "img_idx": img_counter
            })

    image_items = []
    for ib in image_blocks:
        bbox = ib["bbox"]
        rect = fitz.Rect(bbox)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=rect)

        img_name = f"chapter{chapter_idx:02d}_p{page_abs_index+1:04d}_img{ib['img_idx']:02d}.png"
        out_path = os.path.join(out_dir, img_name)
        pix.save(out_path)

        # 이미지 아래 텍스트 1~3개 추출
        local_texts = []
        for tb in text_blocks:
            if tb["index"] <= ib["index"]:
                continue
            if tb["bbox"][1] >= bbox[3] - 5:
                local_texts.append(tb["text"])
                if len(local_texts) >= max_local_blocks:
                    break

        image_items.append({
            "file": img_name,
            "page_number": page_abs_index + 1,
            "bbox": bbox,
            "local_text": local_texts
        })

    return {
        "page_texts": page_texts,
        "images": image_items,
        "meta": {}
    }


# ---------------------------------------------------------
# (C) 수학 전용 페이지 추출 엔진 (math)
#   - 기본 엔진 + 수식 후보 span 수집
# ---------------------------------------------------------
def _extract_page_blocks_math(page, chapter_idx, page_abs_index, out_dir,
                              max_local_blocks=3):
    page_dict = page.get_text("dict")
    blocks = page_dict["blocks"]

    text_blocks = []
    formula_spans = []
    image_blocks = []

    img_counter = 0
    page_texts = []

    math_fonts = ("CambriaMath", "STIX", "TimesNewRomanPS-Italic",
                  "TimesNewRomanPS-ItalicMT")

    for idx, b in enumerate(blocks):
        btype = b.get("type", 0)
        bbox = b.get("bbox", [0, 0, 0, 0])

        if btype == 0:
            text = ""
            for line in b.get("lines", []):
                for span in line.get("spans", []):
                    span_text = span.get("text", "")
                    text += span_text
                    font = span.get("font", "")
                    if font and any(f in font for f in math_fonts):
                        if span_text.strip():
                            formula_spans.append({
                                "text": span_text.strip(),
                                "bbox": span.get("bbox", bbox)
                            })
                text += "\n"
            text = text.strip()
            if text:
                text_blocks.append({
                    "index": idx,
                    "text": text,
                    "bbox": bbox
                })
                page_texts.append(text)

        elif btype == 1:
            img_counter += 1
            image_blocks.append({
                "index": idx,
                "bbox": bbox,
                "img_idx": img_counter
            })

    image_items = []
    for ib in image_blocks:
        bbox = ib["bbox"]
        rect = fitz.Rect(bbox)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=rect)

        img_name = f"chapter{chapter_idx:02d}_p{page_abs_index+1:04d}_img{ib['img_idx']:02d}.png"
        out_path = os.path.join(out_dir, img_name)
        pix.save(out_path)

        local_texts = []
        for tb in text_blocks:
            if tb["index"] <= ib["index"]:
                continue
            if tb["bbox"][1] >= bbox[3] - 5:
                local_texts.append(tb["text"])
                if len(local_texts) >= max_local_blocks:
                    break

        image_items.append({
            "file": img_name,
            "page_number": page_abs_index + 1,
            "bbox": bbox,
            "local_text": local_texts
        })

    return {
        "page_texts": page_texts,
        "images": image_items,
        "meta": {
            "formulas": formula_spans
        }
    }


# ---------------------------------------------------------
# (D) IT 전용 페이지 추출 엔진 (it)
#   - 기본 엔진 + 코드 블록 수집
# ---------------------------------------------------------
def _extract_page_blocks_it(page, chapter_idx, page_abs_index, out_dir,
                            max_local_blocks=3):
    page_dict = page.get_text("dict")
    blocks = page_dict["blocks"]

    text_blocks = []
    code_blocks = []
    image_blocks = []

    img_counter = 0
    page_texts = []

    mono_keywords = ("Consolas", "Courier", "NotoMono", "JetBrainsMono")

    for idx, b in enumerate(blocks):
        btype = b.get("type", 0)
        bbox = b.get("bbox", [0, 0, 0, 0])

        if btype == 0:
            normal_lines = []
            code_lines = []

            for line in b.get("lines", []):
                line_text = ""
                line_mono = False
                for span in line.get("spans", []):
                    span_text = span.get("text", "")
                    font = span.get("font", "")
                    if any(m in font for m in mono_keywords):
                        line_mono = True
                    line_text += span_text
                line_text_stripped = line_text.rstrip("\n")
                if line_mono or line_text_stripped.strip().startswith(("for ", "if ", "while ", "def ", "class ")):
                    code_lines.append(line_text_stripped)
                else:
                    normal_lines.append(line_text_stripped)

            if normal_lines:
                text = "\n".join([ln for ln in normal_lines if ln.strip()])
                if text.strip():
                    text_blocks.append({
                        "index": idx,
                        "text": text.strip(),
                        "bbox": bbox
                    })
                    page_texts.append(text.strip())

            if code_lines:
                code_text = "\n".join([ln for ln in code_lines if ln.strip()])
                code_blocks.append({
                    "index": idx,
                    "code": code_text,
                    "bbox": bbox
                })

        elif btype == 1:
            img_counter += 1
            image_blocks.append({
                "index": idx,
                "bbox": bbox,
                "img_idx": img_counter
            })

    image_items = []
    for ib in image_blocks:
        bbox = ib["bbox"]
        rect = fitz.Rect(bbox)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=rect)

        img_name = f"chapter{chapter_idx:02d}_p{page_abs_index+1:04d}_img{ib['img_idx']:02d}.png"
        out_path = os.path.join(out_dir, img_name)
        pix.save(out_path)

        local_texts = []
        for tb in text_blocks:
            if tb["index"] <= ib["index"]:
                continue
            if tb["bbox"][1] >= bbox[3] - 5:
                local_texts.append(tb["text"])
                if len(local_texts) >= max_local_blocks:
                    break

        image_items.append({
            "file": img_name,
            "page_number": page_abs_index + 1,
            "bbox": bbox,
            "local_text": local_texts
        })

    return {
        "page_texts": page_texts,
        "images": image_items,
        "meta": {
            "code_blocks": code_blocks
        }
    }


# ---------------------------------------------------------
# (E) 경영·경제 전용 페이지 추출 엔진 (biz)
#   - 기본 엔진 + 표/숫자 많은 블록 힌트 저장
# ---------------------------------------------------------
def _extract_page_blocks_biz(page, chapter_idx, page_abs_index, out_dir,
                             max_local_blocks=3):
    page_dict = page.get_text("dict")
    blocks = page_dict["blocks"]

    text_blocks = []
    table_like_blocks = []
    image_blocks = []

    img_counter = 0
    page_texts = []

    for idx, b in enumerate(blocks):
        btype = b.get("type", 0)
        bbox = b.get("bbox", [0, 0, 0, 0])

        if btype == 0:
            text = ""
            for line in b.get("lines", []):
                for span in line.get("spans", []):
                    text += span.get("text", "")
                text += "\n"
            text = text.strip()
            if text:
                # 숫자와 세로줄(열 구분) 존재 여부로 table 후보 판단(간단 추측)
                digit_count = sum(ch.isdigit() for ch in text)
                bar_count = text.count("|")
                if digit_count >= 6 or bar_count >= 2:
                    table_like_blocks.append({
                        "index": idx,
                        "text": text,
                        "bbox": bbox
                    })
                else:
                    text_blocks.append({
                        "index": idx,
                        "text": text,
                        "bbox": bbox
                    })
                    page_texts.append(text)

        elif btype == 1:
            img_counter += 1
            image_blocks.append({
                "index": idx,
                "bbox": bbox,
                "img_idx": img_counter
            })

    image_items = []
    for ib in image_blocks:
        bbox = ib["bbox"]
        rect = fitz.Rect(bbox)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=rect)

        img_name = f"chapter{chapter_idx:02d}_p{page_abs_index+1:04d}_img{ib['img_idx']:02d}.png"
        out_path = os.path.join(out_dir, img_name)
        pix.save(out_path)

        local_texts = []
        for tb in text_blocks:
            if tb["index"] <= ib["index"]:
                continue
            if tb["bbox"][1] >= bbox[3] - 5:
                local_texts.append(tb["text"])
                if len(local_texts) >= max_local_blocks:
                    break

        image_items.append({
            "file": img_name,
            "page_number": page_abs_index + 1,
            "bbox": bbox,
            "local_text": local_texts
        })

    return {
        "page_texts": page_texts,
        "images": image_items,
        "meta": {
            "table_like_blocks": table_like_blocks
        }
    }


# ---------------------------------------------------------
# (F) 공통 래퍼 – domain에 따라 적절한 엔진 호출
#   domain: "default" / "math" / "it" / "biz"
# ---------------------------------------------------------
def extract_page_blocks(page, chapter_idx, page_abs_index, out_dir,
                        domain="default", max_local_blocks=3):
    if domain == "math":
        return _extract_page_blocks_math(
            page, chapter_idx, page_abs_index, out_dir, max_local_blocks
        )
    elif domain == "it":
        return _extract_page_blocks_it(
            page, chapter_idx, page_abs_index, out_dir, max_local_blocks
        )
    elif domain == "biz":
        return _extract_page_blocks_biz(
            page, chapter_idx, page_abs_index, out_dir, max_local_blocks
        )
    else:
        return _extract_page_blocks_default(
            page, chapter_idx, page_abs_index, out_dir, max_local_blocks
        )


# ---------------------------------------------------------
# (G) 한 챕터 전체 추출 – domain별 메타 포함
# ---------------------------------------------------------
def extract_one_chapter(doc, chapter_info, out_root, domain="default"):
    chap_idx = chapter_info["index"]
    title = chapter_info["title"]
    start = chapter_info["start"]
    end = chapter_info["end"]

    save_dir = os.path.join(out_root, f"chapter_{chap_idx:02d}")
    os.makedirs(save_dir, exist_ok=True)

    chapter_data = {
        "chapter_index": chap_idx,
        "title": title,
        "start_page": start + 1,
        "end_page": end,
        "domain": domain,
        "pages": [],
        "images": [],
        "meta": {}
    }

    all_images = []
    all_page_meta = []

    for p in range(start, end):
        page = doc.load_page(p)
        result = extract_page_blocks(
            page, chap_idx, p, save_dir, domain=domain
        )
        chapter_data["pages"].append({
            "page_number": p + 1,
            "text_blocks": result["page_texts"]
        })
        all_images.extend(result["images"])
        all_page_meta.append({
            "page_number": p + 1,
            "meta": result.get("meta", {})
        })

    chapter_data["images"] = all_images
    chapter_data["meta"]["pages"] = all_page_meta

    out_file = os.path.join(save_dir, "chapter.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(chapter_data, f, ensure_ascii=False, indent=2)

    return out_file
