import os

# import shutil
import re
import sys
import logging

import rich
from dotenv import load_dotenv

# import random
# import json
# import json_repair

load_dotenv()

if "./" not in sys.path:
    sys.path.append("./")

from ctn2md.utils.util_file import get_crc32_id
from ctn2md.src.md_info_base import MIFN, MdInfo
from ctn2md.utils.util_logging import setup_logger_handlers
from ctn2md.utils.util_markdown import remove_comment, read_markdown_file


class HeadingStack:
    def __init__(self):
        """初始化堆栈"""
        self._stack = []  # 堆栈，存储当前层级标题
        self._chapter_numbers = []  # 专门跟踪每个层级的编号
        self._log = []  # 日志，用于记录操作历史，便于调试

    def _reset(self, title: str):
        """
        重置堆栈（如遇到一级标题时清空）
        :param title: 一级标题内容
        """
        self._stack = [{"title": title}]
        if len(self._chapter_numbers) > 0:
            self._chapter_numbers = [self._chapter_numbers[0] + 1]
        else:
            self._chapter_numbers = [1]  # 一级标题从 1 开始
        self._log.append(
            f"Reset stack: {self._stack}, chapter_numbers: {self._chapter_numbers}"
        )

    def _adjust_to_level(self, level: int):
        """
        调整编号和堆栈到指定的标题层级：
        - 补齐跳跃层级。
        - 清理过深层级。
        :param level: 标题层级（如 1 表示 `#`）
        """
        # 弹出多余层级
        while len(self._chapter_numbers) > level:
            self._chapter_numbers.pop()
            self._stack.pop()

        # 补齐缺失层级
        if len(self._chapter_numbers) < level:
            for _ in range(len(self._chapter_numbers), level - 1):
                self._chapter_numbers.append(1)
                self._stack.append({"title": f"PL{len(self._stack) + 1}"})

    def push_level(self, level: int, title: str) -> str:
        """
        根据标题层级和内容，更新堆栈并返回章节编号。
        :param level: 标题层级
        :param title: 标题内容
        :return: 生成的章节编号（如 `1.1` 或 `1`）
        """
        if level == 1:
            # 重置堆栈和编号
            self._reset(title)
        else:
            # 调整堆栈到指定层级
            self._adjust_to_level(level)

            # 更新当前层级的编号
            if len(self._chapter_numbers) == level - 1:
                self._chapter_numbers.append(1)
                self._stack.append({"title": title})
            else:
                self._chapter_numbers[-1] += 1
                self._stack[-1] = {"title": title}

        # 生成章节编号
        chapter_number = ".".join(map(str, self._chapter_numbers))
        self._log.append(f"Added title '{title}' at level {level}: {chapter_number}")
        return chapter_number

    def get_hierarchy_desc(self, separator: str = " __ ") -> str:
        """
        返回当前堆栈层级的描述字符串
        :param separator: 分隔符，默认为 " __ "
        :return: 当前层级的描述字符串（如 "Introduction __ Background"）
        """
        return separator.join(item["title"] for item in self._stack)

    def _get_state(self) -> dict:
        """
        获取堆栈和编号的当前状态以及操作日志。
        :return: 堆栈状态和日志
        """
        return {
            "stack": self._stack,
            "chapter_numbers": self._chapter_numbers,
            "log": self._log,
        }


def _filter_headings_for_hierarchy_comments(md_text, md_info):
    """
    在 Markdown 文本的每个标题前插入基于层级的描述注释，
    同时生成标题的章节编号，确保一级标题独立编号，子章节正确继承父级编号。
    支持容错处理输入的标题层级跳跃或逆序。
    """
    lines = md_text.strip().split("\n")
    processed_lines = []
    stack = HeadingStack()  # 使用堆栈对象
    # doc_title = None  # 当前的一级标题
    md_info[MIFN.MD_SECTIONS] = []  # 初始化列表

    for line in lines:
        # 移除 <!-- ... --> 注释
        line = remove_comment(line)

        # 检测是否是标题行
        if line.startswith("#"):
            level = line.count("#")  # 根据 # 的数量确定标题层级
            title = line[level:].strip()  # 提取标题内容

            # 一级标题：重置堆栈
            if level == 1:
                # doc_title = title
                chapter_number = stack.push_level(level, title)  # 使用 push_level 更新堆栈
                ordered_name = f"{chapter_number}) {title}"
                hierarchy_desc = stack.get_hierarchy_desc()

                # 记录到 md_info
                md_info[MIFN.MD_SECTIONS].append(
                    {"hierarchy_desc": hierarchy_desc, "ordered_name": ordered_name}
                )
            else:
                # 调整堆栈深度并添加标题
                chapter_number = stack.push_level(level, title)
                ordered_name = f"{chapter_number}) {title}"
                hierarchy_desc = stack.get_hierarchy_desc()

                # 记录到 md_info
                md_info[MIFN.MD_SECTIONS].append(
                    {"hierarchy_desc": hierarchy_desc, "ordered_name": ordered_name}
                )

            # 生成描述注释
            desc = f"<!-- [ordered_name] {ordered_name} [ordered_name] [desc] {hierarchy_desc} [desc] -->"
            processed_lines.append("")
            processed_lines.append(desc)

        # 无论是否是标题行，都保留原始行
        processed_lines.append(line)

    # 返回处理后的 Markdown 文本
    return "\n".join(processed_lines)


def _clear_section_files(output_dir):
    if not os.path.isdir(output_dir):
        return

    # 正则模式：匹配以 xcs_ 开头，然后跟任何字符串，最后.md 结尾的文件名
    pattern = re.compile(r"^xcs_.*\.md$")

    names = os.listdir(output_dir)
    for name in names:
        # 检查是否符合正则模式
        if pattern.match(name):
            file_path = os.path.join(output_dir, name)
            try:
                os.remove(file_path)
                logging.info(f"Deleted: {file_path}")
            except Exception as e:
                logging.exception(f"Failed to delete {file_path}: {e}")


def _split_sections_to_files_with_desc_and_sequence(markdown_text, md_info):
    """
    将带有 `<!-- [ordered_name] ... [ordered_name] [desc] ... [desc] -->` 标记的 Markdown 文本
    切割为多个部分，保存到指定目录，并使用 `ordered_name` 作为文件名（在前面加上4位递增的数字作为前缀，再跟上一个 `_`）。

    :param markdown_text: 带有描述标记的 Markdown 文本
    :param output_dir: 输出目录路径
    :return: list[str] 所有新生成的文件名
    """
    output_dir = md_info.get_out_dir()
    os.makedirs(output_dir, exist_ok=True)

    crc32_id = get_crc32_id(md_info.get_doc_pathname())

    # 分割 Markdown 行
    lines = markdown_text.strip().split("\n")
    current_section = []
    current_ordered_name = None
    current_desc = None
    created_filenames = []  # 用于存储所有生成的文件名

    # 文件索引：0 用于无 `ordered_name` 的内容，1 开始用于有 `ordered_name` 的内容
    file_index = 1
    saved_no_ordered_name = False

    for line in lines:
        # 检测 `ordered_name` 和 `desc`
        ordered_name, desc = _extract_ordered_and_desc(line)

        if ordered_name:
            # 保存之前的段落
            file_index = _save_current_section(
                output_dir=output_dir,
                file_index=file_index,
                created_filenames=created_filenames,
                section_content="\n".join(current_section),
                ordered_name=current_ordered_name,
                desc=current_desc,
                saved_no_ordered_name=saved_no_ordered_name,
                crc32_id=crc32_id,
            )
            saved_no_ordered_name = saved_no_ordered_name or not current_ordered_name
            current_section = []  # 清空段落内容

            # 更新当前 `ordered_name` 和 `desc`
            current_ordered_name = ordered_name
            current_desc = desc

        # 将当前行归入段落内容
        current_section.append(line)

    # 保存最后一个段落
    _save_current_section(
        output_dir=output_dir,
        file_index=file_index,
        created_filenames=created_filenames,
        section_content="\n".join(current_section),
        ordered_name=current_ordered_name,
        desc=current_desc,
        saved_no_ordered_name=saved_no_ordered_name,
        crc32_id=crc32_id,
    )

    return created_filenames


def _save_current_section(
    output_dir,
    file_index,
    created_filenames,
    section_content,
    ordered_name,
    desc,
    saved_no_ordered_name,
    crc32_id,
):
    """
    保存当前段落到文件。

    :param output_dir: 输出目录路径
    :param file_index: 当前文件索引
    :param created_filenames: 已创建文件名列表
    :param section_content: 要保存的段落内容
    :param ordered_name: 段落的 `ordered_name` 或 None
    :param desc: 段落的 `desc` 或 None
    :param saved_no_ordered_name: 是否已保存无 `ordered_name` 的段落
    :return: 更新后的文件索引
    """
    if not section_content.strip():
        return file_index  # 跳过空内容

    if not ordered_name and not saved_no_ordered_name:
        # 保存无 `ordered_name` 的段落
        file_name = _save_section_to_file(
            output_dir=output_dir,
            file_index=0,
            ordered_name="0_NoHeading",
            desc="NoDescription",
            section_content=section_content,
            crc32_id=crc32_id,
        )
        created_filenames.append(file_name)
    elif ordered_name:
        # 保存有 `ordered_name` 的段落
        file_name = _save_section_to_file(
            output_dir=output_dir,
            file_index=file_index,
            ordered_name=ordered_name,
            desc=desc or "NoDescription",
            section_content=section_content,
            crc32_id=crc32_id,
        )
        created_filenames.append(file_name)
        file_index += 1

    return file_index


def _save_section_to_file(
    output_dir, file_index, ordered_name, desc, section_content, crc32_id
):
    """
    将一个 Markdown 段落保存到文件。
    :param output_dir: 输出目录路径
    :param file_index: 当前文件索引
    :param ordered_name: 当前段落的 `ordered_name`
    :param desc: 当前段落的 `desc`
    :param section_content: 当前段落的完整内容
    :return: str 生成的文件名
    """
    try:
        # 安全处理文件名
        safe_ordered_name = re.sub(r"\)", "-", ordered_name, count=1)
        safe_ordered_name = re.sub(
            r"[^\w\-]", "_", safe_ordered_name
        )  # 非字母、数字、下划线或连字符的字符替换为下划线
        file_name = f"xcs_{crc32_id}_{file_index:04d}_{safe_ordered_name}.md"
        file_path = os.path.join(output_dir, file_name)

        # 写入文件
        with open(file_path, "w", encoding="utf-8") as f:
            if desc:
                f.write(f"<!-- [desc] {desc} [desc] -->\n")
            f.write(section_content)

        logging.info(f"Saved section to file: {file_path}")
        return file_name
    except Exception as e:
        logging.error(f"Error saving section to file: {file_name}")
        logging.exception(e)
        return None


def _extract_ordered_and_desc(line):
    """
    从一行中提取 `ordered_name` 和 `desc` 的内容。
    :param line: 包含注释的 Markdown 行
    :return: (ordered_name, desc) 或 (None, None) 如果未找到
    """
    try:
        # 提取 [ordered_name] 和 [desc] 使用单个正则表达式匹配整个结构
        pattern = r"<!--\s*\[ordered_name\]\s*(.+?)\s*\[ordered_name\]\s*\[desc\]\s*(.+?)\s*\[desc\]\s*-->"
        match = re.search(pattern, line)

        if match:
            ordered_name = match.group(1)
            desc = match.group(2)
            return ordered_name, desc

        # 如果不匹配，返回 None, None
        return None, None
    except Exception as e:
        logging.error(f"Error extracting from line: {line}")
        logging.exception(e)
        return None, None


def inject_section_heirarchy(md_info_path, src_step_num=None, dst_step_num=None):
    logging.info(
        f"##MDFLOW##: fix_section_heirarchy started src_step_num:{src_step_num} dst_step_num:{dst_step_num}..."
    )
    md_info = MdInfo(md_info_path)

    pathname_src_step_md, pathname_dst_step_md = md_info.name_src_n_dst_step_pathname(
        src_step_num, dst_step_num=dst_step_num
    )
    if pathname_src_step_md is None or pathname_dst_step_md is None:
        raise ValueError(f"no {pathname_src_step_md} and {pathname_dst_step_md}")

    md_text = read_markdown_file(pathname_src_step_md)
    md_text_new = _filter_headings_for_hierarchy_comments(md_text, md_info)

    logging.warning(
        f"fix_section_heirarchy: pathname_dst_step_md: {pathname_dst_step_md}"
    )
    with open(pathname_dst_step_md, "w+") as f:
        f.write(md_text_new)

    output_dir = md_info.get_out_dir()
    _clear_section_files(output_dir)
    sdsec_names = _split_sections_to_files_with_desc_and_sequence(md_text_new, md_info)
    md_info[MIFN.FNAMES_SECS] = sdsec_names

    md_info.add_step_into_md_info_mdflow(
        pathname_dst_step_md, actor="fix_section_heirarchy"
    )
    md_info_path = md_info.save()
    logging.info(f"##MDFLOW##: fix_section_heirarchy ended.")
    return md_info_path


if __name__ == "__main__":
    setup_logger_handlers()

    src_step_num = 1
    dst_step_num = 21
    md_info_path = "_output/ctn2md_深度学习在视电阻率快速反演中的研究/_info.json"
    # md_info_path = "_output/ctn2md_-波士顿咨询：银行业生成式AI应用报告（2023）/_info.json"

    md_info_path = inject_section_heirarchy(
        md_info_path, src_step_num=src_step_num, dst_step_num=dst_step_num
    )

    md_info = MdInfo(md_info_path)
    rich.print(md_info)
    print(md_info_path)
