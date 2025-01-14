# import os
import sys
from dataclasses import dataclass

# import logging
import rich
from dotenv import load_dotenv

load_dotenv()

if "./" not in sys.path:
    sys.path.append("./")

from md2vdb.utils.util_tokenizer import get_token_encoding
from md2vdb.src.parse_ordered_name import OrderedNames, parse_ordered_name

MAX_TOKENS_IN_CHUNK = 1024


@dataclass
class ChunkedSectionInfo:
    id: str
    parent: str
    title: str
    desc: str
    max_tokens_in_chunk: int
    doc_path: str
    doc_title: str


def _get_parent_id(id):
    if id.find(".") == -1:
        return ""
    names = id.split(".")
    names = names[0 : len(names) - 1]
    return ".".join(names)


def chunk_section(
    md_section,
    doc_path=None,
    doc_title=None,
    max_tokens_in_chunk=MAX_TOKENS_IN_CHUNK,
    need_desc_at_top=True,
):
    lines = md_section.splitlines()

    ordered_names = None
    total_tokens = 0
    chunks = {}
    chunk_no = 0
    for line in lines:
        if line.startswith("<!-- [desc]"):
            continue
        if line.startswith("<!-- [ordered_name]"):
            if ordered_names is not None:
                raise ValueError("order_names found twice?")
            ordered_names = parse_ordered_name(line)
            if not isinstance(ordered_names, OrderedNames):
                raise ValueError("Not able found all information")
            continue

        if ordered_names is None:
            raise ValueError("not qualified section -- no [ordered_name] found")
        token_count = len(get_token_encoding().encode(line)) + 1
        if total_tokens + token_count > max_tokens_in_chunk:
            chunk_no += 1
            if chunk_no not in chunks:
                chunks[chunk_no] = []
                if need_desc_at_top:
                    chunks[chunk_no].append(f"[desc] {ordered_names.desc} [desc]")
            chunks[chunk_no].append(line)
            total_tokens = token_count
        else:
            if chunk_no not in chunks:
                chunks[chunk_no] = []
                if need_desc_at_top:
                    chunks[chunk_no].append(f"[desc] {ordered_names.desc} [desc]")
            chunks[chunk_no].append(line)
            total_tokens += token_count

    if ordered_names is None:
        raise ValueError("No ordered_name")

    id = ordered_names.order
    parent = _get_parent_id(id)
    title = ordered_names.title
    desc = ordered_names.desc
    max_tokens_in_chunk = max_tokens_in_chunk

    csi = ChunkedSectionInfo(
        id, parent, title, desc, max_tokens_in_chunk, doc_path, doc_title
    )

    return csi, chunks


if __name__ == "__main__":
    pname_md_section = (
        "_work/ctn2md_深度学习在视电阻率快速反演中的研究_lvlm/xcs_6a2683b0_0006_3_1_1-_卷积原理.md"
    )
    doc_path = "_work/ctn2md_深度学习在视电阻率快速反演中的研究_lvlm/深度学习在视电阻率快速反演中的研究.pdf"
    doc_title = "深度学习在视电阻率快速反演中的研究和应用"

    with open(pname_md_section, encoding="utf-8") as f:
        md_section = f.read()

    csi, chunks = chunk_section(
        md_section, doc_path=doc_path, doc_title=doc_title, max_tokens_in_chunk=256
    )
    rich.print(csi)
    rich.print(chunks)
