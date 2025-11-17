# lecturenote

Simple tools to extract a single chapter from a PDF and save as JSON.

Usage (CLI):

python scripts/extract_chapter.py book.pdf 1

GUI: run `scripts/gui_extract.py` to open a small Tkinter app to pick a PDF and extract a chapter.

Notes:
- The extractor prefers PyMuPDF if available, but falls back to pdfplumber (pure Python).
- Some PDFs omit proper ToUnicode mapping; in that case extracted text may appear garbled. Consider enabling OCR fallback.
