# gui_extract.py
# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import threading
import os
import webbrowser
import fitz

import scripts.extract_chapter as extract_chapter
import scripts.easy_explanation_pipeline as explanation_pipeline

ctk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

class FullGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("PDF → User-defined Chapter Extract → Easy Explanation")
        self.geometry("1300x1000")
        self.stop_flag = False

        # Configure grid layout (1x2)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0) # Top
        self.grid_rowconfigure(1, weight=0) # Options
        self.grid_rowconfigure(2, weight=0) # Prompt
        self.grid_rowconfigure(3, weight=0) # Group Opt
        self.grid_rowconfigure(4, weight=1) # Lists
        self.grid_rowconfigure(5, weight=0) # Buttons
        self.grid_rowconfigure(6, weight=0) # Log

        # -------------------------------
        # TOP: 파일 선택
        # -------------------------------
        top = ctk.CTkFrame(self)
        top.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        
        self.pdf_var = tk.StringVar()
        self.out_var = tk.StringVar()

        ctk.CTkLabel(top, text="PDF 파일:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ctk.CTkEntry(top, textvariable=self.pdf_var, width=600).grid(row=0, column=1, padx=5, pady=5)
        ctk.CTkButton(top, text="찾기", command=self.select_pdf, width=80).grid(row=0, column=2, padx=5, pady=5)

        ctk.CTkLabel(top, text="출력 폴더:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        ctk.CTkEntry(top, textvariable=self.out_var, width=600).grid(row=1, column=1, padx=5, pady=5)
        ctk.CTkButton(top, text="찾기", command=self.select_output, width=80).grid(row=1, column=2, padx=5, pady=5)

        ctk.CTkButton(top, text="목차 불러오기", command=self.load_toc).grid(row=2, column=1, pady=5)

        # -------------------------------
        # 요약/추출 옵션
        # -------------------------------
        opt = ctk.CTkFrame(self)
        opt.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(opt, text="요약 형태:").grid(row=0, column=0, padx=5, pady=5)
        self.summary_mode = ctk.CTkComboBox(opt, values=["html", "slide", "markdown", "json", "simple"], width=100)
        self.summary_mode.set("html")
        self.summary_mode.grid(row=0, column=1, padx=5, pady=5)

        ctk.CTkLabel(opt, text="스타일:").grid(row=0, column=2, padx=5, pady=5)
        self.design_style = ctk.CTkComboBox(opt, values=["basic", "slide", "blog", "textbook", "custom"], width=100)
        self.design_style.set("basic")
        self.design_style.grid(row=0, column=3, padx=5, pady=5)

        ctk.CTkLabel(opt, text="그림:").grid(row=0, column=4, padx=5, pady=5)
        self.use_images = ctk.CTkComboBox(opt, values=["include", "no_images"], width=100)
        self.use_images.set("include")
        self.use_images.grid(row=0, column=5, padx=5, pady=5)

        ctk.CTkLabel(opt, text="도메인:").grid(row=0, column=6, padx=5, pady=5)
        self.domain_var = ctk.CTkComboBox(opt, values=["default", "math", "it", "biz"], width=100)
        self.domain_var.set("default")
        self.domain_var.grid(row=0, column=7, padx=5, pady=5)

        ctk.CTkLabel(opt, text="핵심 도식만:").grid(row=0, column=8, padx=5, pady=5)
        self.diagram_only = ctk.CTkComboBox(opt, values=["off", "on"], width=80)
        self.diagram_only.set("off")
        self.diagram_only.grid(row=0, column=9, padx=5, pady=5)

        # -------------------------------
        # 사용자 요약 지시문 입력
        # -------------------------------
        prompt_frame = ctk.CTkFrame(self)
        prompt_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        
        ctk.CTkLabel(prompt_frame, text="사용자 요약 지시문 (선택)").pack(anchor="w", padx=5, pady=2)
        self.user_prompt = ctk.CTkTextbox(prompt_frame, height=60)
        self.user_prompt.pack(fill="x", padx=5, pady=5)

        # -------------------------------
        # 그룹 모드
        # -------------------------------
        group_opt = ctk.CTkFrame(self)
        group_opt.grid(row=3, column=0, padx=10, pady=5, sticky="ew")

        self.group_mode = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(group_opt, text="사용자 지정 그룹 모드", variable=self.group_mode).pack(side="left", padx=10, pady=5)

        ctk.CTkButton(group_opt, text="▶ 선택 항목으로 그룹 생성", command=self.create_group).pack(side="left", padx=10, pady=5)
        ctk.CTkButton(group_opt, text="선택 그룹 삭제", command=self.delete_group, fg_color="transparent", border_width=1).pack(side="left", padx=5, pady=5)

        # -------------------------------
        # TOC 리스트 (좌), 그룹 리스트(우)
        # -------------------------------
        list_frame = ctk.CTkFrame(self)
        list_frame.grid(row=4, column=0, padx=10, pady=5, sticky="nsew")
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_columnconfigure(1, weight=1)
        list_frame.grid_rowconfigure(0, weight=1)

        # ----- 원본 TOC -----
        toc_frame = ctk.CTkFrame(list_frame)
        toc_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        
        ctk.CTkLabel(toc_frame, text="PDF 원본 목차(TOC)").pack(pady=2)

        self.toc_scroll = ctk.CTkScrollableFrame(toc_frame, label_text="")
        self.toc_scroll.pack(fill="both", expand=True, padx=5, pady=5)

        self.toc_vars = {}
        self.toc_items = []  # [{index, title, start, end, level}, ...]

        # ----- 사용자 그룹 -----
        group_frame = ctk.CTkFrame(list_frame)
        group_frame.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        
        ctk.CTkLabel(group_frame, text="사용자 그룹").pack(pady=2)

        # Listbox is not directly available in customtkinter, using standard Listbox with some styling or ScrollableFrame
        # Using ScrollableFrame for better integration
        self.group_scroll = ctk.CTkScrollableFrame(group_frame)
        self.group_scroll.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.group_widgets = [] # To keep track of group widgets for selection
        self.selected_group_index = None

        self.user_groups = []  # [{"group_index":1, "title":"...", "items":[3,4,5], "start":.., "end":..}]

        # -------------------------------
        # 작업 실행 버튼
        # -------------------------------
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=5, column=0, padx=10, pady=5)
        
        ctk.CTkButton(btn_frame, text="선택 챕터 추출", command=self.start_extract, width=200).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="선택 챕터 쉬운 해설서 생성", command=self.start_summary, width=200).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="생성 중단", command=self.stop_summary, fg_color="darkred", width=100).pack(side="left", padx=5)

        # -------------------------------
        # 진행 상태
        # -------------------------------
        self.progress = ctk.CTkProgressBar(self)
        self.progress.grid(row=6, column=0, padx=20, pady=(5,0), sticky="ew")
        self.progress.set(0)

        self.log = ctk.CTkTextbox(self, height=150)
        self.log.grid(row=7, column=0, padx=10, pady=10, sticky="ew")

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
        for w in self.toc_scroll.winfo_children():
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

            var = ctk.BooleanVar()
            chk = ctk.CTkCheckBox(self.toc_scroll, text=text, variable=var)
            chk.pack(anchor="w", pady=2)
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
        if self.selected_group_index is None:
            return messagebox.showwarning("주의", "삭제할 그룹을 선택하세요.")

        idx = self.selected_group_index
        group = self.user_groups[idx]
        del self.user_groups[idx]
        self.selected_group_index = None

        # index 재정렬
        for i, g in enumerate(self.user_groups, start=1):
            g["group_index"] = i

        self.update_group_list()
        self.log_write(f"[그룹 삭제] {group['title']}")

    # -----------------------------------------------------
    # 그룹 표시
    # -----------------------------------------------------
    def update_group_list(self):
        for w in self.group_scroll.winfo_children():
            w.destroy()
        self.group_widgets = []
        
        for i, g in enumerate(self.user_groups):
            txt = f"[그룹 {g['group_index']:02d}] {g['title']} (p {g['start']+1}~{g['end']+1})"
            # Using Button to simulate listbox selection
            btn = ctk.CTkButton(self.group_scroll, text=txt, fg_color="transparent", border_width=1, 
                                text_color=("gray10", "gray90"), anchor="w",
                                command=lambda idx=i: self.select_group(idx))
            btn.pack(fill="x", pady=2)
            self.group_widgets.append(btn)

    def select_group(self, index):
        self.selected_group_index = index
        # Visual feedback
        for i, btn in enumerate(self.group_widgets):
            if i == index:
                btn.configure(fg_color=("gray75", "gray25"))
            else:
                btn.configure(fg_color="transparent")

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

        self.progress.set(0)
        self.stop_flag = False

        # 사용자 추가 요약 지시문 읽기
        custom_prompt = ""
        try:
            custom_prompt = self.user_prompt.get("1.0", "end").strip()
        except Exception:
            custom_prompt = ""

        threading.Thread(
            target=self.summary_worker,
            args=(chapters, use_images, domain, diagram_only, custom_prompt),
            daemon=True,
        ).start()

    # -----------------------------------------------------
    # summary worker
    # -----------------------------------------------------
    def summary_worker(self, chapters, use_images, domain, diagram_only, user_instruction):
        total = len(chapters)
        for i, ch in enumerate(chapters):
            if self.stop_flag:
                self.log_write("[중단됨]")
                break

            chap_dir = ch["dir"]

            self.log_write(f"[요약] {ch['index']} - {ch['title']}")

            def update_progress(v):
                # v is 0.0 to 1.0 for single chapter
                # map to global progress
                # current chapter base: i / total
                # current chapter progress: v / total
                global_p = (i + v) / total
                self.progress.set(global_p)

            def stop_check():
                return self.stop_flag

            try:
                html = explanation_pipeline.easy_explain_chapter(
                    chap_dir,
                    domain=domain,
                    use_images=use_images,
                    diagram_only=diagram_only,
                    progress_callback=update_progress,
                    stop_flag=stop_check,
                    user_instruction=user_instruction,
                )
                out_path = explanation_pipeline.save_explanation(chap_dir, html)
                self.log_write(f"  → 쉬운 해설서 저장: {out_path}")
                try:
                    webbrowser.open(out_path)
                except Exception:
                    pass
            except Exception as e:
                self.log_write(f"  → 쉬운 해설서 생성 실패: {e}")

        self.progress.set(1.0)
        self.log_write("[완료] 요약 생성 종료")

    # -----------------------------------------------------
    # 로그 출력
    # -----------------------------------------------------
    def log_write(self, msg):
        self.log.insert("end", msg + "\n")
        self.log.see("end")


if __name__ == "__main__":
    FullGUI().mainloop()
