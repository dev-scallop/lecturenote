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
        self.title("PDF → Chapter Extract → Easy Summary")
        self.geometry("1150x900")
        self.stop_flag = False

        top = ttk.Frame(self, padding=10)
        top.pack(fill=tk.X)

        self.pdf_var = tk.StringVar()
        self.out_var = tk.StringVar()

        ttk.Label(top, text="PDF 파일:").grid(row=0, column=0)
        ttk.Entry(top, textvariable=self.pdf_var, width=70).grid(row=0, column=1)
        ttk.Button(top, text="찾기", command=self.select_pdf).grid(row=0, column=2)

        ttk.Label(top, text="출력 폴더:").grid(row=1, column=0)
        ttk.Entry(top, textvariable=self.out_var, width=70).grid(row=1, column=1)
        ttk.Button(top, text="찾기", command=self.select_output).grid(row=1, column=2)

        ttk.Button(top, text="챕터 분석", command=self.load_chapters)\
            .grid(row=2, column=1, pady=8)

        # 요약 형태 선택
        opt_mode = ttk.Frame(self, padding=10)
        opt_mode.pack(fill=tk.X)

        ttk.Label(opt_mode, text="요약 형태:").pack(side=tk.LEFT)
        self.summary_mode = tk.StringVar(value="html")
        ttk.Combobox(
            opt_mode,
            textvariable=self.summary_mode,
            values=["html", "slide", "markdown", "json", "simple"],
            width=15
        ).pack(side=tk.LEFT)

        # 디자인 스타일 선택
        opt_style = ttk.Frame(self, padding=10)
        opt_style.pack(fill=tk.X)

        ttk.Label(opt_style, text="디자인 스타일:").pack(side=tk.LEFT)
        self.design_style = tk.StringVar(value="basic")
        ttk.Combobox(
            opt_style,
            textvariable=self.design_style,
            values=["basic", "slide", "blog", "textbook", "custom"],
            width=15
        ).pack(side=tk.LEFT)

        # 그림 포함 여부 선택
        opt_img = ttk.Frame(self, padding=10)
        opt_img.pack(fill=tk.X)

        ttk.Label(opt_img, text="그림 포함 여부:").pack(side=tk.LEFT)
        self.use_images = tk.StringVar(value="include")
        ttk.Combobox(
            opt_img,
            textvariable=self.use_images,
            values=["include", "no_images"],
            width=15
        ).pack(side=tk.LEFT)

        # 도서 분야 선택 (default/math/it/biz)
        opt_domain = ttk.Frame(self, padding=10)
        opt_domain.pack(fill=tk.X)

        ttk.Label(opt_domain, text="도서 분야:").pack(side=tk.LEFT)
        # 내부 값은 영어 코드, 표시 텍스트는 한글
        self.domain_var = tk.StringVar(value="default")

        self.domain_combo = ttk.Combobox(
            opt_domain,
            textvariable=self.domain_var,
            values=["default", "math", "it", "biz"],
            width=15
        )
        self.domain_combo.pack(side=tk.LEFT)

        ttk.Label(opt_domain, text=" (default: 일반 / math: 수학 / it: IT / biz: 경영·경제)").pack(side=tk.LEFT)

        # 챕터 선택 영역
        self.chapter_frame = ttk.LabelFrame(self, text="챕터 선택", padding=10)
        self.chapter_frame.pack(fill=tk.BOTH, expand=True, padx=10)

        self.chapter_list = []
        self.chapter_vars = {}

        # 실행 버튼들
        ttk.Button(self, text="선택 챕터 추출", command=self.start_extract)\
            .pack(pady=4)
        ttk.Button(self, text="선택 챕터 요약 생성", command=self.start_summary)\
            .pack(pady=4)
        ttk.Button(self, text="요약 중단", command=self.stop_summary)\
            .pack(pady=4)

        # 진행바 + 로그
        self.progress = ttk.Progressbar(self, length=820)
        self.progress.pack(pady=6)

        self.log = tk.Text(self, height=18)
        self.log.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # -----------------------------------------
    # 파일/폴더 선택
    # -----------------------------------------
    def select_pdf(self):
        p = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if p:
            self.pdf_var.set(p)

    def select_output(self):
        p = filedialog.askdirectory()
        if p:
            self.out_var.set(p)

    # -----------------------------------------
    # 챕터 분석 (TOC 기반)
    # -----------------------------------------
    def load_chapters(self):
        pdf = self.pdf_var.get()
        if not pdf:
            return messagebox.showerror("오류", "PDF 파일을 선택하세요.")

        doc = fitz.open(pdf)
        chapters = extract_chapter.find_chapter_starts(doc)
        doc.close()

        self.chapter_list = chapters
        self.chapter_vars = {}

        for w in self.chapter_frame.winfo_children():
            w.destroy()

        for ch in chapters:
            var = tk.BooleanVar()
            self.chapter_vars[ch["index"]] = var
            txt = f"Chapter {ch['index']:02d}: {ch['title']} / (p {ch['start']+1}~{ch['end']})"
            ttk.Checkbutton(self.chapter_frame, text=txt, variable=var)\
                .pack(anchor="w")

        self.log_write(f"[INFO] 챕터 {len(chapters)}개 분석 완료")

    # -----------------------------------------
    # 챕터 추출
    # -----------------------------------------
    def start_extract(self):
        pdf = self.pdf_var.get()
        out = self.out_var.get()
        if not pdf or not out:
            return messagebox.showerror("오류", "PDF/출력 폴더를 확인하세요.")

        selected = [ch for ch in self.chapter_list
                    if self.chapter_vars.get(ch["index"], tk.BooleanVar()).get()]
        if not selected:
            return messagebox.showwarning("주의", "추출할 챕터를 선택하세요.")

        domain = self.domain_var.get() or "default"

        threading.Thread(
            target=self.extract_worker,
            args=(pdf, out, selected, domain),
            daemon=True
        ).start()

    def extract_worker(self, pdf, out, chapters, domain):
        doc = fitz.open(pdf)
        for ch in chapters:
            self.log_write(f"[추출] Chapter {ch['index']} - {ch['title']} (domain={domain})")
            result = extract_chapter.extract_one_chapter(doc, ch, out, domain=domain)
            self.log_write(f"  → 저장됨: {result}")
        doc.close()
        self.log_write("[완료] 챕터 추출 종료")

    # -----------------------------------------
    # 요약 중단
    # -----------------------------------------
    def stop_summary(self):
        self.stop_flag = True
        self.log_write("[중단 요청됨]")

    # -----------------------------------------
    # 요약 생성
    # -----------------------------------------
    def start_summary(self):
        out = self.out_var.get()
        if not out:
            return messagebox.showerror("오류", "출력 폴더를 먼저 선택하세요.")

        selected = [ch for ch in self.chapter_list
                    if self.chapter_vars.get(ch["index"], tk.BooleanVar()).get()]
        if not selected:
            return messagebox.showwarning("주의", "요약할 챕터를 선택하세요.")

        self.progress["value"] = 0
        self.stop_flag = False

        mode = self.summary_mode.get()
        style = self.design_style.get()
        use_images = self.use_images.get()
        domain = self.domain_var.get() or "default"

        threading.Thread(
            target=self.summary_worker,
            args=(out, selected, mode, style, use_images, domain),
            daemon=True
        ).start()

    def summary_worker(self, out_dir, chapters, mode, style, use_images, domain):
        for ch in chapters:
            if self.stop_flag:
                self.log_write("[중단됨]")
                break

            chap_dir = os.path.join(out_dir, f"chapter_{ch['index']:02d}")
            self.log_write(
                f"[요약] Chapter {ch['index']} - {ch['title']} "
                f"(mode={mode}, style={style}, images={use_images}, domain={domain})"
            )

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
                progress_callback=update_progress,
                stop_flag=stop_check
            )

            out_path = summary_pipeline.save_summary(chap_dir, text, mode)
            self.log_write(f"  → 요약 저장: {out_path}")

            try:
                webbrowser.open(out_path)
            except Exception:
                pass

        self.log_write("[완료] 요약 생성 종료")

    # -----------------------------------------
    # 로그 출력
    # -----------------------------------------
    def log_write(self, msg):
        self.log.insert(tk.END, msg + "\n")
        self.log.see(tk.END)


if __name__ == "__main__":
    FullGUI().mainloop()
