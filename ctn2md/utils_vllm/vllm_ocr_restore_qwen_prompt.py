PROMPT_INSTRUCT_OCR_QWEN_START = """
# Task:
Perform OCR on the image.
- Recognize printed text only, ignore handwriting and images.
- Convert tables to Markdown format.
- Use headings, paragraphs, and lists for structure.
- Ignore headers and footers.
- For figures: use `![Figure X](Figure X "caption")`.

# Output:
- Provide the first portion of text in Markdown format.
- Add "[ocr_end]" only when all OCR content has been output.
"""

PROMPT_INSTRUCT_OCR_QWEN_CONTINUE = """
# Task:
Continue the OCR task and provide the next portion in Markdown format.
- Add "[ocr_end]" only when all OCR content has been output.
"""

PROMPT_INSTRUCT_OCR_QWEN_SINGLE = """
# Task:
Perform OCR on the image.
- Recognize printed text only, ignore handwriting and images.
- Convert tables to Markdown format.
- Use headings, paragraphs, and lists for structure.
- Ignore headers and footers.
- For figures: use `![Figure X](Figure X "caption")`.

# Output:
- Provide the full portion of text in Markdown format.

"""