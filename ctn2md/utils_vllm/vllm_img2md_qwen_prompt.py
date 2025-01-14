PROMPT_INSTRUCT_IMG2MD_QWEN_START = """
# Task:
Convert the following page into Markdown format, ensuring completeness and maintaining the original layout order.
- Recognize and convert text, lists, tables, and images:
  - **Lists**: Use Markdown list format (`-` for unordered, numbers for ordered).
  - **Tables**: Use Markdown table format.
  - **Images**: Embed using `![Figure X](LocalImageFileName "caption")`.
- Use headings, paragraphs, lists, and tables for structure.
- Ignore headers and footers.
- **Important**: Ensure the output text's language matches the original content exactly. **Do not translate** any text, and maintain the original language.

{inst_img_rects}

# Output:
- Provide the first portion of the content in Markdown format.
- Add "[ocr_end]" only when all content has been output.

"""

PROMPT_INSTRUCT_IMG2MD_QWEN_START_IMG_RECTS = """
- Red boxes (**red_rects**) indicate areas that may contain images, charts, or lists: ({img_rects}).
"""

PROMPT_INSTRUCT_IMG2MD_QWEN_CONTINUE = """
# Task:
Continue the OCR task and provide the next portion of the content in Markdown format.
- Add "[ocr_end]" only when all content has been output.
"""
