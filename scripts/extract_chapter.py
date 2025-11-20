# extract_chapter.py
# -*- coding: utf-8 -*-
import fitz  # PyMuPDF
import os
import json
import re


# ---------------------------------------------------------
# 캡션 패턴 인식 ("그림 3-1 ...", "표 4-2 ..." 등)
# ---------------------------------------------------------
CAPTION_PATTERN = re.compile(
    r'^(그림|표)\s*\d+[\-\.]\d+(\s+.+)?$'
)

def _is_caption_text(text: str) -> bool:
    """텍스트가 '그림 1-1 …' 또는 '표 2-3 …' 패턴인지 판별"""
    if not text:
        return False
    t = text.strip()
    if CAPTION_PATTERN.match(t):
        return True
    # 영어 버전도 허용
    tl = t.lower()
    if tl.startswith("figure ") or tl.startswith("fig ") or tl.startswith("fig.") or tl.startswith("table "):
        return True
    return False


# ---------------------------------------------------------
# PDF TOC 가져오기 (GUI에서 사용할 목록)
# ---------------------------------------------------------
def get_toc_items(doc):
    toc = doc.get_toc()
    if not toc:
        raise RuntimeError("PDF에 목차(TOC)가 없습니다.")

    items = []
    n = len(toc)
    page_count = doc.page_count

    for i, (level, title, page) in enumerate(toc):
        start = max(page - 1, 0)
        if i == n - 1:
            end = page_count - 1
        else:
            end = max(toc[i + 1][2] - 2, start)

        items.append({
            "index": i + 1,
            "level": level,
            "title": title or "",
            "start": start,
            "end": end,
        })
    return items


# ---------------------------------------------------------
# 텍스트 블록 추출
# ---------------------------------------------------------
def _extract_text_blocks(page):
    blocks = page.get_text("dict")["blocks"]
    text_blocks = []
    page_texts = []

    for idx, b in enumerate(blocks):
        if b.get("type", 0) != 0:
            continue

        txt = ""
        for line in b.get("lines", []):
            for span in line.get("spans", []):
                txt += span.get("text", "")
            txt += "\n"

        txt = txt.strip()
        if txt:
            text_blocks.append({
                "index": idx,
                "text": txt,
                "bbox": b.get("bbox"),
            })
            page_texts.append(txt)

    return text_blocks, page_texts


# ---------------------------------------------------------
# 도식/표 벡터 rect 후보 얻기
# ---------------------------------------------------------
def _get_diagram_rects(page, min_size=50):
    """
    page.get_drawings() 에서 path 단위로 추출한 rect 들 중
    도식 가능성이 있는 것만 필터링.
    """
    rects = []
    for d in page.get_drawings():
        r = d.get("rect")
        if not r:
            continue
        x0, y0, x1, y1 = r
        w, h = x1 - x0, y1 - y0

        # 너무 작은 장식 요소 제거
        if w < min_size or h < min_size:
            continue

        rects.append(fitz.Rect(x0, y0, x1, y1))

    return rects


# ---------------------------------------------------------
# 캡션 아래쪽/위쪽 rect 중 관련 있는 것만 모아 union
# ---------------------------------------------------------
def _union_diagram_for_caption(caption_bbox, diagram_rects, max_distance=700):
    cx0, cy0, cx1, cy1 = caption_bbox

    candidates = []
    for r in diagram_rects:
        # 도식은 보통 caption 위에 위치
        if r.y1 > cy0 + 5:  
            continue

        # caption과 너무 떨어진 도형은 제외
        if (cy0 - r.y1) > max_distance:
            continue

        # 가로 겹침 필터 (너무 좌우로 떨어진 도형은 제외)
        if r.x1 < cx0 - 80 or r.x0 > cx1 + 80:
            continue

        candidates.append(r)

    if not candidates:
        return None

    # 여러 rect 를 하나의 큰 bbox 로 merge
    x0 = min(r.x0 for r in candidates)
    y0 = min(r.y0 for r in candidates)
    x1 = max(r.x1 for r in candidates)
    y1 = max(r.y1 for r in candidates)

    return fitz.Rect(x0, y0, x1, y1)


# ---------------------------------------------------------
# 페이지 내 이미지/도식/표 추출 핵심
# ---------------------------------------------------------
def _process_images(page, chapter_idx, page_abs_index, out_dir, text_blocks):
    images = []
    diagram_rects = _get_diagram_rects(page)

    diagram_counter = 0

    # 캡션 기준으로 도식/표 추출
    for tb in text_blocks:
        text = tb["text"]
        if not _is_caption_text(text):
            continue

        caption = text.strip()
        cap_bbox = tb["bbox"]

        # 1) 캡션과 가장 관련 있는 도식 rect들을 union
        diag_rect = _union_diagram_for_caption(cap_bbox, diagram_rects)
        if diag_rect is None:
            continue

        # 2) 렌더링
        pix = page.get_pixmap(
            matrix=fitz.Matrix(3, 3),
            clip=diag_rect
        )

        diagram_counter += 1
        fname = f"chapter{chapter_idx:02d}_p{page_abs_index+1:04d}_diagram{diagram_counter:02d}.png"
        save_path = os.path.join(out_dir, fname)
        pix.save(save_path)

        # 3) caption 뒤 몇 개 텍스트를 local_text 로
        local_list = []
        for tb2 in text_blocks:
            if tb2["index"] <= tb["index"]:
                continue
            if len(local_list) >= 3:
                break
            local_list.append(tb2["text"])

        # 4) kind 판정
        kind = "figure"
        cap_low = caption.lower()
        if caption.startswith("표") or cap_low.startswith("table"):
            kind = "table"

        images.append({
            "file": fname,
            "page_number": page_abs_index + 1,
            "bbox": list(diag_rect),
            "caption": caption,
            "local_text": local_list,
            "kind": kind
        })

    return images


# ---------------------------------------------------------
# 페이지 분석
# ---------------------------------------------------------
def extract_page_blocks(page, chapter_idx, page_abs_index, out_dir, domain="default"):
    text_blocks, page_texts = _extract_text_blocks(page)
    images = _process_images(page, chapter_idx, page_abs_index, out_dir, text_blocks)

    return {
        "page_texts": page_texts,
        "images": images,
        "meta": {}
    }


# ---------------------------------------------------------
# chapter.json 생성
# ---------------------------------------------------------
def extract_one_chapter(doc, chapter_info, out_root, domain="default"):
    idx = chapter_info["index"]
    start = chapter_info["start"]
    end = chapter_info["end"]
    title = chapter_info["title"]

    save_dir = os.path.join(out_root, f"chapter_{idx:02d}")
    os.makedirs(save_dir, exist_ok=True)

    chapter_data = {
        "chapter_index": idx,
        "title": title,
        "start_page": start + 1,
        "end_page": end + 1,
        "domain": domain,
        "pages": [],
        "images": [],
        "meta": {}
    }

    all_images = []
    all_meta = []

    for p in range(start, end + 1):
        page = doc.load_page(p)
        result = extract_page_blocks(page, idx, p, save_dir, domain)

        chapter_data["pages"].append({
            "page_number": p + 1,
            "text_blocks": result["page_texts"]
        })

        all_images.extend(result["images"])
        all_meta.append({
            "page_number": p + 1,
            "meta": result.get("meta", {})
        })

    chapter_data["images"] = all_images
    chapter_data["meta"]["pages"] = all_meta

    out_path = os.path.join(save_dir, "chapter.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(chapter_data, f, ensure_ascii=False, indent=2)

    return out_path
