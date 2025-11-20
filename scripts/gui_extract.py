# gui_extract.py
# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import webbrowser
import fitz

import extract_chapter
import summary_pipeline


class FullGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PDF → User-defined Chapter Extract → Summary")
        self.geometry("1300x1000")
        self.stop_flag = False

        # -------------------------------
        # TOP: 파일 선택
        # -------------------------------
        top = ttk.Frame(self, padding=10)
        top.pack(fill=tk.X)

        self.pdf_var = tk.StringVar()
        self.out_var = tk.StringVar()

        ttk.Label(top, text="PDF 파일:").grid(row=0, column=0)
        ttk.Entry(top, textvariable=self.pdf_var, width=80).grid(row=0, column=1)
        ttk.Button(top, text="찾기", command=self.select_pdf).grid(row=0, column=2)

        ttk.Label(top, text="출력 폴더:").grid(row=1, column=0)
        ttk.Entry(top, textvariable=self.out_var, width=80).grid(row=1, column=1)
        ttk.Button(top, text="찾기", command=self.select_output).grid(row=1, column=2)

        ttk.Button(top, text="목차 불러오기", command=self.load_toc).grid(row=2, column=1, pady=8)

        # -------------------------------
        # 요약/추출 옵션
        # -------------------------------
        opt = ttk.Frame(self, padding=10)
        opt.pack(fill=tk.X)

        ttk.Label(opt, text="요약 형태:").grid(row=0, column=0)
        self.summary_mode = tk.StringVar(value="html")
        ttk.Combobox(opt, textvariable=self.summary_mode,
                     values=["html", "slide", "markdown", "json", "simple"],
                     width=12).grid(row=0, column=1)

        ttk.Label(opt, text="스타일:").grid(row=0, column=2)
        self.design_style = tk.StringVar(value="basic")
        ttk.Combobox(opt, textvariable=self.design_style,
                     values=["basic", "slide", "blog", "textbook", "custom"],
                     width=12).grid(row=0, column=3)

        ttk.Label(opt, text="그림:").grid(row=0, column=4)
        self.use_images = tk.StringVar(value="include")
        ttk.Combobox(opt, textvariable=self.use_images,
                     values=["include", "no_images"],
                     width=12).grid(row=0, column=5)

        ttk.Label(opt, text="도메인:").grid(row=0, column=6)
        self.domain_var = tk.StringVar(value="default")
        ttk.Combobox(opt, textvariable=self.domain_var,
                     values=["default", "math", "it", "biz"],
                     width=12).grid(row=0, column=7)

        ttk.Label(opt, text="핵심 도식만:").grid(row=0, column=8)
        self.diagram_only = tk.StringVar(value="off")
        ttk.Combobox(opt, textvariable=self.diagram_only,
                     values=["off", "on"],
                     width=12).grid(row=0, column=9)

        # -------------------------------
        # 사용자 요약 지시문 입력
        # -------------------------------
        prompt_frame = ttk.LabelFrame(self, text="사용자 요약 지시문 (선택)", padding=10)
        prompt_frame.pack(fill=tk.X)

        self.user_prompt = tk.Text(prompt_frame, height=4)
        self.user_prompt.pack(fill=tk.X)

        # -------------------------------
        # 그룹 모드
        # -------------------------------
        group_opt = ttk.Frame(self, padding=10)
        group_opt.pack(fill=tk.X)

        self.group_mode = tk.BooleanVar(value=False)
        ttk.Checkbutton(group_opt, text="사용자 지정 그룹 모드", variable=self.group_mode).pack(side=tk.LEFT)

        ttk.Button(group_opt, text="▶ 선택 항목으로 그룹 생성",
                   command=self.create_group).pack(side=tk.LEFT, padx=10)
        ttk.Button(group_opt, text="선택 그룹 삭제",
                   command=self.delete_group).pack(side=tk.LEFT, padx=5)

        # -------------------------------
        # TOC 리스트 (좌), 그룹 리스트(우)
        # -------------------------------
        list_frame = ttk.Frame(self, padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True)

        # ----- 원본 TOC -----
        toc_frame = ttk.LabelFrame(list_frame, text="PDF 원본 목차(TOC)", padding=5)
        toc_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.toc_canvas = tk.Canvas(toc_frame)
        self.toc_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        toc_scroll = ttk.Scrollbar(toc_frame, orient="vertical", command=self.toc_canvas.yview)
        toc_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.toc_canvas.configure(yscrollcommand=toc_scroll.set)

        self.toc_inner = ttk.Frame(self.toc_canvas)
        self.toc_canvas.create_window((0, 0), window=self.toc_inner, anchor="nw")

        self.toc_inner.bind("<Configure>", lambda e:
                            self.toc_canvas.configure(scrollregion=self.toc_canvas.bbox("all")))

        self.toc_vars = {}
        self.toc_items = []  # [{index, title, start, end, level}, ...]

        # ----- 사용자 그룹 -----
        group_frame = ttk.LabelFrame(list_frame, text="사용자 그룹", padding=5)
        group_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.group_listbox = tk.Listbox(group_frame, height=30)
        self.group_listbox.pack(fill=tk.BOTH, expand=True)

        self.user_groups = []  # [{"group_index":1, "title":"...", "items":[3,4,5], "start":.., "end":..}]

        # -------------------------------
        # 작업 실행 버튼
        # -------------------------------
        ttk.Button(self, text="선택 챕터 추출", command=self.start_extract).pack(pady=4)
        ttk.Button(self, text="선택 챕터 요약 생성", command=self.start_summary).pack(pady=4)
        ttk.Button(self, text="요약 중단", command=self.stop_summary).pack(pady=4)

        # -------------------------------
        # 진행 상태
        # -------------------------------
        self.progress = ttk.Progressbar(self, length=1100)
        self.progress.pack(pady=6)

        self.log = tk.Text(self, height=18)
        self.log.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # -----------------------------------------------------
    # PDF / 폴더
    # -----------------------------------------------------
    def select_pdf(self):
        p = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if p:
            self.pdf_var.set(p)

    def select_output(self):
        p = filedialog.askdirectory()
        if p:
            self.out_var.set(p)

    # -----------------------------------------------------
    # PDF TOC 불러오기
    # -----------------------------------------------------
    def load_toc(self):
        pdf = self.pdf_var.get()
        if not pdf:
            return messagebox.showerror("오류", "PDF 파일을 선택하세요.")

        doc = fitz.open(pdf)
        try:
            self.toc_items = extract_chapter.get_toc_items(doc)
        finally:
            doc.close()

        # 기존 위젯 초기화
        for w in self.toc_inner.winfo_children():
            w.destroy()
        self.toc_vars = {}

        # 목록 다시 그리기
        for item in self.toc_items:
            idx = item["index"]
            title = item["title"]
            start = item["start"]
            end = item["end"]
            level = item["level"]

            indent = "    " * (level - 1)
            text = f"{indent}[{idx:02d}] {title} (p {start+1}~{end+1})"

            var = tk.BooleanVar()
            chk = ttk.Checkbutton(self.toc_inner, text=text, variable=var)
            chk.pack(anchor="w")
            self.toc_vars[idx] = var

        self.log_write(f"[INFO] 목차 항목 {len(self.toc_items)}개 불러옴")

    # -----------------------------------------------------
    # 그룹 생성
    # -----------------------------------------------------
    def create_group(self):
        if not self.group_mode.get():
            return messagebox.showwarning("주의", "먼저 '사용자 지정 그룹 모드'를 선택하세요.")

        selected = [i for i, item in enumerate(self.toc_items, start=1)
                    if self.toc_vars[i].get()]

        if not selected:
            return messagebox.showwarning("주의", "그룹으로 묶을 항목을 선택하세요.")

        # 연속성 검사
        for i in range(len(selected) - 1):
            if selected[i + 1] != selected[i] + 1:
                return messagebox.showerror("오류", "연속된 항목만 그룹으로 묶을 수 있습니다.")

        # 그룹 정보 만들기
        items = [self.toc_items[i - 1] for i in selected]
        title = items[0]["title"] or f"그룹{len(self.user_groups)+1}"

        start = min(x["start"] for x in items)
        end = max(x["end"] for x in items)

        group = {
            "group_index": len(self.user_groups) + 1,
            "title": title,
            "items": selected,
            "start": start,
            "end": end
        }
        self.user_groups.append(group)

        # 그룹 생성 후 사용한 항목은 자동으로 선택 해제
        for idx in selected:
            if idx in self.toc_vars:
                self.toc_vars[idx].set(False)

        self.update_group_list()
        self.log_write(f"[그룹 생성] {title} (p {start+1}~{end+1})")

    # -----------------------------------------------------
    # 그룹 삭제
    # -----------------------------------------------------
    def delete_group(self):
        sel = self.group_listbox.curselection()
        if not sel:
            return messagebox.showwarning("주의", "삭제할 그룹을 선택하세요.")

        idx = sel[0]
        group = self.user_groups[idx]
        del self.user_groups[idx]

        # index 재정렬
        for i, g in enumerate(self.user_groups, start=1):
            g["group_index"] = i

        self.update_group_list()
        self.log_write(f"[그룹 삭제] {group['title']}")

    # -----------------------------------------------------
    # 그룹 표시
    # -----------------------------------------------------
    def update_group_list(self):
        self.group_listbox.delete(0, tk.END)
        for g in self.user_groups:
            txt = f"[그룹 {g['group_index']:02d}] {g['title']} (p {g['start']+1}~{g['end']+1})"
            self.group_listbox.insert(tk.END, txt)

    # -----------------------------------------------------
    # 추출 시작
    # -----------------------------------------------------
    def start_extract(self):
        pdf = self.pdf_var.get()
        out = self.out_var.get()
        if not pdf or not out:
            return messagebox.showerror("오류", "PDF 파일과 출력 폴더를 확인하세요.")

        domain = self.domain_var.get() or "default"

        # 그룹이 있으면 → 그룹 기준
        if self.user_groups:
            chapters = [{
                "index": i + 1,
                "title": g["title"],
                "start": g["start"],
                "end": g["end"]
            } for i, g in enumerate(self.user_groups)]
        else:
            # TOC 항목 그대로 챕터로 사용
            chapters = [{
                "index": i + 1,
                "title": item["title"],
                "start": item["start"],
                "end": item["end"],
            } for i, item in enumerate(self.toc_items)]

        threading.Thread(
            target=self.extract_worker, args=(pdf, out, chapters, domain), daemon=True
        ).start()

    # -----------------------------------------------------
    # 추출 worker
    # -----------------------------------------------------
    def extract_worker(self, pdf, out, chapters, domain):
        doc = fitz.open(pdf)
        for ch in chapters:
            self.log_write(f"[추출] {ch['index']} - {ch['title']}")
            result = extract_chapter.extract_one_chapter(doc, ch, out, domain=domain)
            self.log_write(f"  → 저장됨: {result}")
        doc.close()
        self.log_write("[완료] 챕터 추출 종료")

    # -----------------------------------------------------
    # 요약
    # -----------------------------------------------------
    def stop_summary(self):
        self.stop_flag = True
        self.log_write("[중단 요청됨]")

    def start_summary(self):
        out = self.out_var.get()
        if not out:
            return messagebox.showerror("오류", "출력 폴더를 먼저 선택하세요.")

        mode = self.summary_mode.get()
        style = self.design_style.get()
        use_images = self.use_images.get()
        domain = self.domain_var.get()
        diagram_only = (self.diagram_only.get() == "on")

        # 그룹 우선
        if self.user_groups:
            chapters = [{
                "index": i + 1,
                "title": g["title"],
                "dir": os.path.join(out, f"chapter_{i+1:02d}")
            } for i, g in enumerate(self.user_groups)]
        else:
            chapters = [{
                "index": i + 1,
                "title": item["title"],
                "dir": os.path.join(out, f"chapter_{i+1:02d}")
            } for i, item in enumerate(self.toc_items)]

        self.progress["value"] = 0
        self.stop_flag = False

        # 사용자 추가 요약 지시문 읽기
        custom_prompt = ""
        try:
            custom_prompt = self.user_prompt.get("1.0", tk.END).strip()
        except Exception:
            custom_prompt = ""

        threading.Thread(
            target=self.summary_worker,
            args=(chapters, mode, style, use_images, domain, diagram_only, custom_prompt),
            daemon=True
        ).start()

    # -----------------------------------------------------
    # summary worker
    # -----------------------------------------------------
    def summary_worker(self, chapters, mode, style, use_images, domain, diagram_only, user_instruction):
        for ch in chapters:
            if self.stop_flag:
                self.log_write("[중단됨]")
                break

            chap_dir = ch["dir"]

            self.log_write(f"[요약] {ch['index']} - {ch['title']}")

            def update_progress(v):
                self.progress["value"] = v * 100

            def stop_check():
                return self.stop_flag

            text = summary_pipeline.summarize_chapter(
                chap_dir,
                mode=mode,
                style=style,
                use_images=use_images,
                domain=domain,
                diagram_only=diagram_only,
                progress_callback=update_progress,
                stop_flag=stop_check,
                user_instruction=user_instruction,
            )

            out_path = summary_pipeline.save_summary(chap_dir, text, mode)
            self.log_write(f"  → 요약 저장: {out_path}")

            try:
                webbrowser.open(out_path)
            except:
                pass

        self.log_write("[완료] 요약 생성 종료")

    # -----------------------------------------------------
    # 로그 출력
    # -----------------------------------------------------
    def log_write(self, msg):
        self.log.insert(tk.END, msg + "\n")
        self.log.see(tk.END)


if __name__ == "__main__":
    FullGUI().mainloop()
