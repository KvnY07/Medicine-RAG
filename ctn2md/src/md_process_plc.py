from dotenv import load_dotenv
#import os
import sys
#import logging
import rich
import re

load_dotenv()

if "./" not in sys.path:
    sys.path.append("./")


"""
    注释中参数解释 <!-- PLC: ... -->:
    1. Page:X/Y
        - X: 当前页码，从 1 开始计数。
        - Y: 文档总页数，由 total_pages 指定。
    2. Line:X/Y
        - X: 标题行在整个文档中的实际行号，从 1 开始计数。
        - Y: 文档的总行数。
    3. Chars:X/Y
        - X: 当前标题以下、下一个标题以上的字符数。
        - Y: 当前页面的总字符数，包含所有非图片内容。
    4. PlcId: 
        "p{page_number}s{section_number}"
"""

_PLC_COMMENT = """<!-- PLC: Page:{current_page}/{total_pages}, Line:{line_number}/{total_lines}, Chars:{content_char_count}/{total_char_count}, PlcId:{plc_id} -->"""
_PLC_ID = "p{pid}s{sid}"

def extract_plc_info_from_comment(line):
    """
    提取 Markdown 行中 <!-- PLC: ... --> 的结构化内容。

    参数:
        line (str): Markdown 文本行。

    返回:
        dict or None: 提取的内容，返回字典包含 `Page`、`Line` 和 `Chars` 信息。
                      如果行中没有 PLC 注释，返回 None。
    """
    match = re.search(r'<!-- PLC: Page:(\d+)/(\d+), Line:(\d+)/(\d+), Chars:(\d+)/(\d+), PlcId:p(\d+)s(\d+) -->', line)
    if match:
        return {
            "Page": {"current": int(match.group(1)), "total": int(match.group(2))},
            "Line": {"current": int(match.group(3)), "total": int(match.group(4))},
            "Chars": {"current": int(match.group(5)), "total": int(match.group(6))},
            "PlcId": f"p{match.group(7)}s{match.group(8)}"
        }
    match = re.search(r'Page:(\d+)/(\d+), Line:(\d+)/(\d+), Chars:(\d+)/(\d+), PlcId:p(\d+)s(\d+)', line)
    if match:
        return {
            "Page": {"current": int(match.group(1)), "total": int(match.group(2))},
            "Line": {"current": int(match.group(3)), "total": int(match.group(4))},
            "Chars": {"current": int(match.group(5)), "total": int(match.group(6))},
            "PlcId": f"p{match.group(7)}s{match.group(8)}"
        }
    return None

def separate_heading_and_plc_comment(line, with_plc_id=False):
    """
    分解 Markdown 标题行，提取前半部分的标题和后续的 PLC 注释。

    参数:
        line (str): Markdown 标题行，可能包含 <!-- PLC: ... --> 注释。

    返回:
        tuple: 包含两个元素的元组：
            - heading (str): 标题部分。
            - plc_comment (str or None): 提取的 PLC 注释内容（不包含 <!-- -->）。
                                        如果没有 PLC 注释，则为 None。
    """
    # 使用正则分解标题部分和 PLC 注释
    # pattern = r'^(.*?)(<!-- PLC: (.*?) -->)?$',
    pattern_no_plc_id = r'^(.*?)<!-- PLC: (Page:\d+/\d+, Line:\d+/\d+, Chars:\d+/\d+).*?-->'
    pattern_with_plc_id = r'^(.*?)<!-- PLC: (Page:\d+/\d+, Line:\d+/\d+, Chars:\d+/\d+, PlcId:p\d+s\d+).*?-->'
    if not with_plc_id:
        pattern = pattern_no_plc_id
    else:
        pattern = pattern_with_plc_id 

    match = re.match(pattern, line.strip())
    if match:
        heading = match.group(1).strip()  # 提取标题部分
        plc_comment = match.group(2).strip() if match.group(2) else None  # 提取 PLC 注释内容
        return heading, plc_comment
    return line, ""  # 如果不匹配，返回原始行和 None

def _count_chars(text):
    """
    统计文本中的字符数，忽略 Markdown 特殊符号和图片引用。
    """
    # 移除 Markdown 特殊符号和图片引用
    text = re.sub(r'[>#*_\-`~\[\]]', '', text)  # 去掉 Markdown 符号
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)  # 去掉图片引用
    text = re.sub(r'\s+', '', text)             # 去掉空白符
    return len(text)

def has_injected_plc_comment(line):
    if line is None:
        return False 
    if line.find("<!-- PLC:") != -1:
        return True 
    return False

def inject_plc_comment_to_page(md_page, page_number, total_pages, md_info):
    """
    注入统计信息到 Markdown 文档标题行。
    :param md_page: str, 当前页面的 Markdown 内容
    :param page_ndx: int, 当前页码（从 0 开始计数）
    :param total_pages: int, 文档总页数
    :param md_info: dict, 包含整个文档的信息（例如标题等，暂未使用）
    :return: str, 注入统计信息后的 Markdown 文档内容
    """

    # 分割 Markdown 文档为行，并确定总行数
    lines = md_page.split('\n')
    total_lines = len(lines)

    # 使用正则提取标题和其内容范围
    sections = []
    current_section = {"title": None, "lines": []}
    first_section_no_heading = None 

    has_heading = False
    for line in lines:
        if re.match(r'^#+\s', line):  # 如果是标题行
            has_heading = True
            # 如果当前有积累的标题范围，保存
            if current_section["title"]:
                sections.append(current_section)

            if current_section["title"] is None:
                if len(current_section["lines"]) > 0:
                    first_section_no_heading = current_section
            # 开始一个新的标题范围
            current_section = {"title": line, "lines": []}
        else:
            # 非标题行，归属于当前标题范围
            current_section["lines"].append(line)
    # 最后一个标题范围
    if current_section["title"]:
        sections.append(current_section)

    if not has_heading:
        first_section_no_heading = current_section

    # 计算总字符数
    total_char_count = sum(
        _count_chars(line) for line in lines
    )

    # 结果行列表
    result_lines = []
    if first_section_no_heading is not None:
        result_lines.extend(first_section_no_heading["lines"])

    for sec_ndx, section in enumerate(sections):
        title = section["title"]
        content_lines = section["lines"]
        content_char_count = sum(_count_chars(line) for line in content_lines)

        plc_id = _PLC_ID.format(pid=page_number, sid=sec_ndx+1)

        # 注释信息
        line_number = lines.index(title) + 1
        injected_title = f"{title} "
        injected_title += _PLC_COMMENT.format(current_page=page_number,
                                              total_pages=total_pages,
                                              line_number=line_number,
                                              total_lines=total_lines,
                                              content_char_count=content_char_count,
                                              total_char_count=total_char_count,
                                              plc_id=plc_id)
        ##<!-- PLC: Page:{page_number}/{total_pages}, Line:{line_number}/{total_lines}, Chars:{content_char_count}/{total_char_count} PlcId:{} -->"
        result_lines.append(injected_title)
        result_lines.extend(content_lines)

    return '\n'.join(result_lines)


def _find_first_plc_info_no_heading(heading_pattern, org_lines):
    lines_without_heading = []
    first_plc_line_ndx = None
    first_plc_info_no_heading = None
    for ndx, line in enumerate(org_lines):
        line = line.strip()
        if len(line) == 0:
            continue
        if first_plc_line_ndx is None:
            first_plc_line_ndx = ndx

        match = re.match(heading_pattern, line)
        if not match:
            lines_without_heading.append(line)
        else:
            if len(lines_without_heading) != 0:
                parts = line.split("<!--")
                if len(parts) == 2:
                    plc_comment = "<!--" + parts[1]
                    first_plc_info = extract_plc_info_from_comment(plc_comment)
                    if first_plc_info is not None:
                        first_plc_info_no_heading = first_plc_info.copy()
                        first_plc_info_no_heading["Line"] = {"current": first_plc_line_ndx, "total":len(lines_without_heading)}
                        first_plc_info_no_heading["Chars"] = {"current": _count_chars("".join(lines_without_heading)), "total":_count_chars("".join(lines_without_heading))}
                        return first_plc_info_no_heading
            break
    return None 

def get_all_normalized_headings_with_plc_info(md_text, fix_first_line_no_heading=True):
    # 定义正则匹配 Markdown Heading 的模式
    heading_pattern = r"^(#{1,6})(\s*)(.+)$"

    heading_n_plc_lines = []
    # 规整化处理 Markdown 文本
    normalized_lines = []

    org_lines = md_text.splitlines()

    first_plc_info_nh = None
    if fix_first_line_no_heading:
        first_plc_info_nh = _find_first_plc_info_no_heading(heading_pattern, org_lines)
  
    first_line_no_heading = None
    for ndx, line in enumerate(org_lines):
        match = re.match(heading_pattern, line)
        if len(line.strip()) != 0:
            if first_line_no_heading is None:
                if not match:
                    if first_plc_info_nh is not None:
                        plc_comment = _PLC_COMMENT.format(current_page=1,
                                                          total_pages=first_plc_info_nh["Page"]["total"],
                                                          line_number=first_plc_info_nh["Line"]["current"],
                                                          total_lines=first_plc_info_nh["Line"]["total"],
                                                          content_char_count=first_plc_info_nh["Chars"]["total"],
                                                          total_char_count=first_plc_info_nh["Chars"]["total"],
                                                          plc_id=_PLC_ID.format(pid=0, sid=0))
                        first_line_no_heading = "## " + line.strip() + " " + plc_comment
                        line = first_line_no_heading
                        match = re.match(heading_pattern, line)

        if match:
            if first_line_no_heading is None:
                first_line_no_heading = ""

            # 提取 # 符号 和 heading 的内容
            hashes = match.group(1)
            content = match.group(3).strip()  # 去掉多余的空格
            normalized_line = f"{hashes} {content}"
            normalized_lines.append(normalized_line)

            heading_line, plc_comment = separate_heading_and_plc_comment(normalized_line)
            heading_n_plc_lines.append((heading_line, plc_comment))
        else:
            normalized_lines.append(line)

    return normalized_lines, heading_n_plc_lines, first_line_no_heading


if __name__ == "__main__":
    md_path_name = "_work/md_samples/深度学习在视电阻率快速反演中的研究___pdf_s0.md"

    with open(md_path_name, 'r') as f:
        md_text = f.read()

    #md_text_plc = inject_plc_comment_to_page()
    #print(md_text)

    normalized_lines, heading_n_plc_lines, first_line_no_heading = get_all_normalized_headings_with_plc_info(md_text)
    rich.print(normalized_lines[:20])
    rich.print("heading_n_plc_lines", heading_n_plc_lines)
    rich.print("first_line_no_heading", first_line_no_heading)

