from dotenv import load_dotenv
import os
import sys
import logging
import rich
#import random
#import re
#import shutil

load_dotenv()

if "./" not in sys.path:
    sys.path.append("./")

from ctn2md.utils.util_logging import setup_logger_handlers
from ctn2md.src.md_info_base import MdInfo, MIFN, FHL_QUALITY_TYPE
from ctn2md.utils.util_ctn_type import CTN_TYPE
from ctn2md.src.ctn2md_gen_md_base import GenMd_Base


def gen_md_unstructured(doc_pathname, out_dir):
    from ctn2md.gen_usio.gen_markdown_unstructured import generate_markdown_unstructured
    logging.info(f"##MDFLOW##: gen_md_unstructured started...")

    md_info = MdInfo(out_dir)
    md_info.set_gen_engine(f"unstructured")
    md_info.set_doc_pathname(doc_pathname)
    md_info[MIFN.FHL_QUALITY] = FHL_QUALITY_TYPE.LOW

    md_info_path = generate_markdown_unstructured(md_info)

    logging.info(f"##MDFLOW##: gen_md_unstructured end")
    return md_info_path


class GenMd_Unstructured(GenMd_Base):
    SUPPORT_CNT_TYPES = [CTN_TYPE.PDF, CTN_TYPE.PPT, CTN_TYPE.DOC]
    OD_SUFFIX = "usio"

    @classmethod
    def generate_markdown(cls,
                          doc_pathname, 
                          out_dir=None, 
                          enforced_gen=False, 
                          mdcontrols=None):
        if not cls.does_support_doc_type(doc_pathname):
            raise ValueError(f"GenMd_Unstructured does not support '{doc_pathname}'")

        md_info, gen_needed = cls.does_gen_needed(doc_pathname, out_dir, enforced_gen)

        if isinstance(mdcontrols, dict):
            md_info.update_mdcontrols(mdcontrols)
            md_info.save()

        if gen_needed:
            md_info_path = gen_md_unstructured(doc_pathname, out_dir)
            if md_info_path is None:
                return None

        return md_info.get_md_info_path()


if __name__ == "__main__":
    #doc_pathname = "datasrc/test/raw_docs/AIGC时代的人力资源管理进化(徐刚).pdf"
    #doc_pathname = "datasrc/test/raw_docs/业绩案例、上汽内外饰DRE外包框架服务合同.pdf"
    #doc_pathname = "datasrc/test/raw_docs/1. 座椅STO间隙 P1.pptx"
    #doc_pathname = "datasrc/test/raw_docs/管理者角色定位与认知课程大纲.docx"
    #doc_pathname = "datasrc/test/raw_docs/考勤修改统一规则.xlsx"
    #doc_pathname = "datasrc/test/raw_docs/5. back panel 与环境匹配工程校核_P2.pptx"
    
    #doc_pathname = "datasrc/exam/raw_docs/ChatGPT intimates a tantalizing future_compressed.pdf"
    doc_pathname = "datasrc/exam/raw_docs/深度学习在视电阻率快速反演中的研究.pdf"

    out_dir = MdInfo.get_suggested_out_dir(doc_pathname, suffix=GenMd_Unstructured.OD_SUFFIX)

    setup_logger_handlers()
    os.makedirs(out_dir, exist_ok=True)
    md_info_path = gen_md_unstructured(doc_pathname, out_dir)
    print(md_info_path)

    md_info = MdInfo(md_info_path)
    rich.print(md_info)
    print(md_info_path)