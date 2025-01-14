import re
from dataclasses import dataclass

import rich


@dataclass
class OrderedNames:
    order: str
    title: str
    desc: str


def parse_ordered_name(line):
    # 正则表达式匹配结构：
    # 1) [ordered_name] 和 [ordered_name] 之间的层级标识（数字.数字.数字）
    # 2) 层级标识后面的标题
    # 3) [desc] 和 [desc] 之间的内容作为 desc
    pattern = re.compile(
        r"""
        \[ordered_name\]\s*         # 匹配[ordered_name]，后面可能有空格
        (?P<order>[\d\.]+)          # 匹配层级标识，格式为数字.数字.数字，如 1.4.6
        \)\s*                        # 匹配右括号
        (?P<title>.*?)               # 匹配标题内容（非贪婪模式，直到下一个标记）
        \[ordered_name\]\s*          # 匹配结束的[ordered_name]标签
        \[desc\]\s*(?P<desc>.*?)\s*\[desc\]  # 匹配[desc]和[desc]之间的内容，作为desc
    """,
        re.VERBOSE | re.DOTALL,
    )

    # 搜索匹配
    match = pattern.search(line)

    if match:
        order = match.group("order")
        title = match.group("title").strip()
        desc = match.group("desc").strip()
        return OrderedNames(order, title, desc)
    else:
        return None


if __name__ == "__main__":
    line = "<!-- [ordered_name] 1) 深度学习在视电阻率快速反演中的研究 [ordered_name] [desc] 深度学习在视电阻率快速反演中的研究 [desc] -->"
    ret = parse_ordered_name(line)
    rich.print(ret)

    line = "<!-- [ordered_name] 3.2.1) 卷积层与 BN 层参数融合 [ordered_name] [desc] 深度学习卷积和重参数化原理 __ 重参数化原理 __ 卷积层与 BN 层参数融合 [desc] -->"
    ret = parse_ordered_name(line)
    rich.print(ret)
