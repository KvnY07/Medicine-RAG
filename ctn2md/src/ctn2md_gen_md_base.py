import os
import sys

from dotenv import load_dotenv

# import logging
# import rich
# import random
# import re
# import shutil

load_dotenv()

if "./" not in sys.path:
    sys.path.append("./")

# from ctn2md.utils.util_logging import setup_logger_handlers
from ctn2md.src.md_info_base import MdInfo
from ctn2md.utils.util_ctn_type import CTN_TYPE


class GenMd_Base:
    SUPPORT_CNT_TYPES = []
    OD_SUFFIX = ""

    @classmethod
    def does_gen_needed(cls, doc_pathname, out_dir, enforced_gen):
        if out_dir is not None:
            out_dir = MdInfo.get_suggested_out_dir(doc_pathname, suffix=cls.OD_SUFFIX)

        gen_needed = False
        md_info = None

        if enforced_gen:
            gen_needed = True
        else:
            pname_md_info = os.path.join(out_dir, MdInfo.get_fname_md_info())
            if not os.path.isfile(pname_md_info):
                gen_needed = True
            else:
                md_info = MdInfo(out_dir)
                pathname_s0_md = md_info.name_step_pathname(0)
                if (pathname_s0_md is None) or (not os.path.exists(pathname_s0_md)):
                    gen_needed = True

        if md_info is None:
            md_info = MdInfo(out_dir)
        return md_info, gen_needed

    @classmethod
    def migrate_md_info(cls, md_info):
        return

    @classmethod
    def does_support_doc_type(cls, doc_pathname):
        ctn_type = CTN_TYPE.get_ctn_type_by_doc_pathname(doc_pathname)
        if ctn_type in cls.SUPPORT_CNT_TYPES:
            return True
        return False

    @classmethod
    def need_followup_step(cls, step_name):
        if step_name == "fix_headings_plc_by_llm":
            return True
        return True
