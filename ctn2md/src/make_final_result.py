import os
import sys

# import random
import json
import shutil
import logging

import rich
from dotenv import load_dotenv

load_dotenv()

if "./" not in sys.path:
    sys.path.append("./")

from ctn2md.src.md_info_base import MIFN, PUBLIC_MIFN, MdInfo
from ctn2md.utils.util_logging import setup_logger_handlers
from ctn2md.utils.util_markdown import find_all_image_refs


def _copy_last_step_as_final(md_info):
    last_step_num = md_info.get_last_step_num()
    pathname_step_md = md_info.name_step_pathname(last_step_num)
    pathname_final_md = md_info.name_step_pathname(-1)

    if os.path.isfile(pathname_final_md):
        os.unlink(pathname_final_md)
    shutil.copy(pathname_step_md, pathname_final_md)
    return pathname_final_md


def _move_aux_files_pages(md_info, out_dir, aux_dir):
    os.makedirs(aux_dir, exist_ok=True)
    fnames_pages = md_info.get_fnames_pages()
    if len(fnames_pages) == 0:
        return False

    fnames_pages_aux = []
    for fname_page in fnames_pages:
        if aux_dir in fname_page:
            continue
        if len(os.path.dirname(fname_page)) != 0:
            continue
        src_pathname = os.path.join(out_dir, fname_page)
        dst_pathname = os.path.join(aux_dir, fname_page)
        if os.path.isfile(src_pathname):
            shutil.move(src_pathname, dst_pathname)
            dst_fname = dst_pathname.replace(out_dir + "/", "")
            fnames_pages_aux.append(dst_fname)

    # update to reflex the move
    md_info_fanems_pages = md_info[MIFN.FNAMES_MD_PAGES]
    for ndx, fname_page in enumerate(md_info_fanems_pages):
        for fname_page_aux in fnames_pages_aux:
            if fname_page in fname_page_aux:
                md_info_fanems_pages[ndx] = fname_page_aux


def _move_aux_files_images(md_info, out_dir, aux_dir):
    last_step_num = md_info.get_last_step_num()
    pathname_step_md = md_info.name_step_pathname(last_step_num)
    image_refs = find_all_image_refs(pathname_step_md)

    os.makedirs(aux_dir, exist_ok=True)
    fnames_images = md_info.get(PUBLIC_MIFN.FNAMES_IMGS, [])
    if len(fnames_images) == 0:
        return False

    for ndx, fname_img in enumerate(fnames_images):
        if aux_dir in fname_img:
            continue
        if len(os.path.dirname(fname_img)) != 0:
            continue

        if fname_img in image_refs:
            continue

        src_pathname = os.path.join(out_dir, fname_img)
        dst_pathname = os.path.join(aux_dir, fname_img)
        if os.path.isfile(src_pathname):
            shutil.move(src_pathname, dst_pathname)
            dst_fname = dst_pathname.replace(out_dir + "/", "")
            fnames_images[ndx] = dst_fname


def _move_aux_files_tables(md_info, out_dir, aux_dir):
    os.makedirs(aux_dir, exist_ok=True)
    fnames_tbls = md_info.get(MIFN.FNAMES_MD_TBLS, [])
    if len(fnames_tbls) == 0:
        return False

    for ndx, fname_tbl in enumerate(fnames_tbls):
        if aux_dir in fname_tbl:
            continue
        if len(os.path.dirname(fname_tbl)) != 0:
            continue

        src_pathname = os.path.join(out_dir, fname_tbl)
        dst_pathname = os.path.join(aux_dir, fname_tbl)
        if os.path.isfile(src_pathname):
            shutil.move(src_pathname, dst_pathname)
            dst_fname = dst_pathname.replace(out_dir + "/", "")
            fnames_tbls[ndx] = dst_fname


def _move_aux_files(md_info):
    out_dir = md_info.get_out_dir()
    aux_dir = md_info.get_aux_dir()

    os.makedirs(aux_dir, exist_ok=True)
    _move_aux_files_pages(md_info, out_dir, aux_dir)
    _move_aux_files_images(md_info, out_dir, aux_dir)
    _move_aux_files_tables(md_info, out_dir, aux_dir)


def _add_sum_json_to_finial_info(md_info, md_final_info):
    out_dir = md_info.get_out_dir()
    pname_final_sum = os.path.join(out_dir, md_info[PUBLIC_MIFN.FNAME_FINAL_SUM])
    with open(pname_final_sum, "r", encoding="utf-8") as f:
        sum = json.load(f)
    md_final_info[PUBLIC_MIFN.DOC_SUMMARY] = {}
    for key, val in sum.items():
        md_final_info[PUBLIC_MIFN.DOC_SUMMARY][key] = val
        if key == "title":
            md_final_info[PUBLIC_MIFN.DOC_LOGIC_TITLE] = val
            md_final_info[PUBLIC_MIFN.DOC_NAME_TITLE] = md_info.get_doc_title()


def _copy_final_result_json(md_info):
    md_final_info = {}
    _add_sum_json_to_finial_info(md_info, md_final_info)

    names = [
        PUBLIC_MIFN.VERSION,
        PUBLIC_MIFN.GEN_ENGINE,
        PUBLIC_MIFN.PATHNAME_ORG_DOC,
        PUBLIC_MIFN.FNAME_ORG_DOC,
        PUBLIC_MIFN.DOC_UNIQUE_ID,
        PUBLIC_MIFN.DOC_CTN_TYPE,
        PUBLIC_MIFN.DOC_NAME_TITLE,
        PUBLIC_MIFN.DOC_LOGIC_TITLE,
        PUBLIC_MIFN.FNAME_FINAL_MD,
        PUBLIC_MIFN.FNAME_FINAL_SUM,
        PUBLIC_MIFN.FNAMES_SECS,
        PUBLIC_MIFN.FNAMES_IMGS,
        PUBLIC_MIFN.FNAMES_SNPS,
    ]
    for name in names:
        if name in md_info:
            if name in md_info:
                md_final_info[name] = md_info[name]

    output_dir = md_info.get_out_dir()
    pathname_final_json = os.path.join(output_dir, md_info.get_fname_final_json())

    with open(pathname_final_json, "w", encoding="utf-8") as f:
        json.dump(md_final_info, f, indent=4, ensure_ascii=False)
    logging.info(f"pathname_final_json: {pathname_final_json}")
    return pathname_final_json


def make_final_json(md_info_path):
    logging.info(f"##MDFLOW##: make_final_md started...")
    md_info = MdInfo(md_info_path)

    move_aux_files = md_info.get_md_control("mctl_move_aux_files", True)
    if move_aux_files:
        _move_aux_files(md_info)

    pathname_final_md = _copy_last_step_as_final(md_info)
    md_info[PUBLIC_MIFN.FNAME_FINAL_MD] = os.path.basename(pathname_final_md)
    md_info.save()

    pathname_final_json = _copy_final_result_json(md_info)
    logging.info(f"##MDFLOW##: make_final_md ended: move_aux_files: {move_aux_files}.")
    logging.info(f"##MDFLOW##: Final md can be found at: '{pathname_final_md}'")
    return pathname_final_json


def reset_md_flow(md_info_path):
    md_info = MdInfo(md_info_path)
    dict_md_flow = md_info.get(MIFN.MDFLOW, None)
    if dict_md_flow is not None:
        for key in list(dict_md_flow.keys()):
            if key != "0":
                del dict_md_flow[key]
    md_info.save()


if __name__ == "__main__":
    setup_logger_handlers()

    # md_info_path = "_output/ctn2md_深度学习在视电阻率快速反演中的研究/_info.json"
    # md_info_path = "_output/ctn2md_YOU_ONLY_2409_13695v1_lvlm/_info.json"
    md_info_path = "_output/ctn2md_业绩案例_上汽内外饰DRE外包框架服务合同_lp/_info.json"

    pathname_final_json = make_final_json(md_info_path)
    print(pathname_final_json)

    md_info = MdInfo(pathname_final_json)
    rich.print(md_info)
    print(pathname_final_json)
