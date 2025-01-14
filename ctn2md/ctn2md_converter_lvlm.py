import os
import sys
import logging

import rich
from dotenv import load_dotenv

# import random
# import json
# import shutil

load_dotenv()

if "./" not in sys.path:
    sys.path.append("./")

if __name__ == "__main__":
    from dotenv import find_dotenv

    _root_dir = os.path.abspath(os.path.dirname(find_dotenv()))
    os.chdir(_root_dir)

from ctn2md.src.md_info_base import MdInfo
from ctn2md.utils.util_logging import setup_logger_handlers
from ctn2md.src.make_final_result import reset_md_flow, make_final_json
from ctn2md.src.ctn2md_gen_md_lvlm import GenMd_Lvlm
from ctn2md.src.ctn2md_fix_heading_plc import fix_headings_plc_by_llm
from ctn2md.src.ctn2md_summarize_content import summarize_content_by_llm
from ctn2md.src.ctn2md_inject_section_hierarchy import inject_section_heirarchy


def _do_content2md_convert_core_lvlm(
    doc_pathname, out_dir=None, enforced_gen=False, mdcontrols=None
):
    if out_dir is None:
        out_dir = MdInfo.get_suggested_out_dir(
            doc_pathname, suffix=GenMd_Lvlm.OD_SUFFIX
        )
    logging.warning(f"work out_dir: {out_dir}")
    os.makedirs(out_dir, exist_ok=True)

    md_generator = GenMd_Lvlm
    if md_generator is None:
        logging.error("")
        return None

    md_info_path = md_generator.generate_markdown(
        doc_pathname, out_dir=out_dir, enforced_gen=enforced_gen, mdcontrols=mdcontrols
    )
    if md_info_path is None:
        logging.error(f"DCCCV: failed {md_info_path} @initial_gen_md_by_llamaparse")
        return None

    reset_md_flow(md_info_path)

    src_step_num = 0
    if md_generator.need_followup_step("fix_headings_plc_by_llm"):
        md_info_path = fix_headings_plc_by_llm(md_info_path, src_step_num=src_step_num)
        if md_info_path is None:
            logging.error(f"DCCCV: failed {md_info_path} @fix_headings_plc_by_llm")
            return None

    src_step_num += 1
    md_info_path = inject_section_heirarchy(md_info_path, src_step_num=src_step_num)
    if md_info_path is None:
        logging.error(f"DCCCV: failed {md_info_path} @inject_section_heirarchy")
        return None

    src_step_num += 1
    md_info_path = summarize_content_by_llm(md_info_path, src_step_num=src_step_num)
    if md_info_path is None:
        logging.error(f"DCCCV: failed {md_info_path} @summarize_content_by_llm")
        return None

    pathname_final_json = make_final_json(md_info_path)

    return pathname_final_json


def do_content2md_convert(
    doc_pathname, out_dir=None, enforced_gen=False, mdcontrols=None
):
    pathname_final_json = None
    try:
        pathname_final_json = _do_content2md_convert_core_lvlm(
            doc_pathname,
            out_dir=out_dir,
            enforced_gen=enforced_gen,
            mdcontrols=mdcontrols,
        )
    except Exception as ex:
        logging.exception(ex)
        raise ex
    return pathname_final_json


if __name__ == "__main__":
    setup_logger_handlers()

    # doc_pathname = "datasrc/test/raw_docs/AIGC时代的人力资源管理进化(徐刚).pdf"
    # doc_pathname = "datasrc/test/raw_docs/业绩案例、上汽内外饰DRE外包框架服务合同.pdf"
    # doc_pathname = "datasrc/test/raw_docs/业绩案例、上汽内外饰部CAD外包框架服务合同.pdf"
    # doc_pathname = "datasrc/test/raw_docs/业绩案例、比亚迪SJ项目低压线束设计技术服务合同（电子电器）.pdf"
    # doc_pathname = "datasrc/test/raw_docs/业绩案例、比亚迪ST2H项目低压线束设计技术服务合同（电子电器）.pdf"
    # doc_pathname = "datasrc/test/raw_docs/业绩案例、比亚迪车架总成技术服务合同.pdf"
    # doc_pathname = "datasrc/test/raw_docs/业绩案例、比亚迪铝大梁式车架及副车架设计外包中标通知书.pdf"
    # doc_pathname = "datasrc/test/raw_docs/业绩案例、比亚迪驻场线束设计技术服务合同（电子电器）.pdf"
    # doc_pathname = "datasrc/test/raw_docs/1. 座椅STO间隙 P1.pptx"
    # doc_pathname = "datasrc/exam/raw_docs/2. 座垫与钢丝间隙 P1.pptx"
    # doc_pathname = "datasrc/exam/raw_docs/3. 头枕杆圆角定义 P1.pptx"
    # doc_pathname = "datasrc/exam/raw_docs/4. 前后排座椅间距定义 P1.pptx"
    # doc_pathname = "datasrc/test/raw_docs/5. back panel 与环境匹配工程校核_P2.pptx"
    # doc_pathname = "datasrc/exam/raw_docs/6. 前后排座椅H点距离要求 P1.pptx"
    # doc_pathname = "datasrc/test/raw_docs/管理者角色定位与认知课程大纲.docx"
    # doc_pathname = "datasrc/test/raw_docs/考勤修改统一规则.xlsx"
    # doc_pathname = "datasrc/test/raw_docs/高效沟通之黄金三角模型课程大纲.docx"

    # doc_pathname = "datasrc/exam/raw_docs/深度学习在视电阻率快速反演中的研究.pdf"
    # doc_pathname = "datasrc/exam/raw_docs/ChatGPT intimates a tantalizing future_compressed.pdf"
    # doc_pathname = "datasrc/exam/raw_docs/Long-Context LLMs Meet RAG_compressed.pdf"
    # doc_pathname = "datasrc/exam/raw_docs/0530-大模型微调培训-VisualGLM.pdf"
    # doc_pathname = "datasrc/exam/raw_docs/ai602-波士顿咨询：银行业生成式AI应用报告（2023）.pdf"
    # doc_pathname = "datasrc/exam/raw_docs/AI未来十年_大模型产业落地的机遇与挑战_大数据研究院.pptx"
    # doc_pathname = "datasrc/exam/raw_docs/YOU ONLY 2409.13695v1.pdf"
    # doc_pathname = "datasrc/exam/raw_docs/LongRAG.pdf"
    # doc_pathname = "datasrc/exam/raw_docs/DIFFERENTIAL TRANSFORMER 2410.05258v1.pdf"
    # doc_pathname = "datasrc/exam/raw_docs/Winning Solution For Meta KDD Cup’ 24 2410.00005v1.pdf"
    # doc_pathname = "datasrc/exam/raw_docs/attention_is_all_you_need.pdf"
    # doc_pathname = "datasrc/exam/raw_docs/Regioselective hydroxylation of cholecalciferol.pdf"
    # doc_pathname = "datasrc/exam/raw_docs/Survey of different Large Language Model Architectures.pdf"
    # doc_pathname = "datasrc/exam/raw_docs/A Coin Has Two Sides.pdf"

    # doc_pathname = "datasrc/exam/raw_docs/3_20240131104523599_rearranged.pdf"
    doc_pathname = r"E:\test\test\业绩案例、比亚迪SJ项目低压线束设计技术服务合同（电子电器）.pdf"

    mdcontrols = None
    # mdcontrols = {"mctl_lvlm_region_model": "qwen"}

    out_dir = None
    enforced_gen = False

    pathname_final_json = do_content2md_convert(
        doc_pathname, out_dir=out_dir, enforced_gen=enforced_gen, mdcontrols=mdcontrols
    )
    print(pathname_final_json)

    md_info = MdInfo(pathname_final_json)
    rich.print(md_info)
    print(pathname_final_json)
