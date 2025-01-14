import os
import sys

# from typing import List, Tuple # , Optional  # , Dict
import logging

import rich

# import fitz  # PyMuPDF
# import shapely.geometry as sg
# from shapely.geometry.base import BaseGeometry
# from shapely.validation import explain_validity

if "./" not in sys.path:
    sys.path.append("./")

from ctn2md.src.md_info_base import MIFN
from ctn2md.gen_lvlm.lvlm_base import is_in_repair_mode
from ctn2md.utils.util_logging import setup_logger_handlers
from ctn2md.utils_vllm.vllm_img2md_gpt import generate_full_mds_from_image_gpt
from ctn2md.utils_vllm.vllm_img2md_qwen import generate_full_mds_from_image_qwen


def _does_page_need_gen(md_info, page_index, pname_page_md):
    if not os.path.isfile(pname_page_md):
        return True
    if is_in_repair_mode(md_info):
        mctl_lvlm_repair_pages = md_info.get_md_control("mctl_lvlm_repair_pages", [])
        if page_index in mctl_lvlm_repair_pages:
            return True
        return False
    return True


def convert_images_to_mds(md_info, image_infos):
    # pathname_doc = md_info.get_doc_pathname()
    output_dir = md_info.get_out_dir()
    aux_dir = md_info.get_aux_dir()

    pnames_page_md = []
    fnames_imgs = []
    fnames_snps = []
    fnames_page_md_gen = []
    mctl_lvlm_img2md_model = md_info.get_md_control("mctl_lvlm_img2md_model", "gpt")
    mctl_lvlm_notouch_pages = md_info.get_md_control_notouch(
        "mctl_lvlm_notouch_pages", []
    )

    logging.info(
        f"GITM: generate pages from images, is_in_repair_mode: {is_in_repair_mode(md_info)}"
    )
    for ndx, image_info in enumerate(image_infos):
        page_index = ndx + 1
        fname_page_name, fname_page_rect_name, fname_rect_images = image_info
        rich.print(page_index, fname_page_name, fname_page_rect_name, fname_rect_images)

        pname_image = os.path.join(output_dir, fname_page_rect_name)
        rects_img = None
        if len(fname_rect_images) > 0:
            rects_img = fname_rect_images

        fname_page_md = f"page_{page_index}.md"
        pname_page_md = os.path.join(aux_dir, fname_page_md)
        if _does_page_need_gen(md_info, page_index, pname_page_md):

            if page_index not in mctl_lvlm_notouch_pages:
                logging.info(f"GPL: generate page {page_index}...")

                try:
                    if mctl_lvlm_img2md_model == "qwen":
                        md_page = generate_full_mds_from_image_qwen(
                            pname_image, rects_img
                        )
                    else:
                        md_page = generate_full_mds_from_image_gpt(
                            pname_image, rects_img
                        )
                except Exception as ex:
                    md_page = f"\n**Failed to generate content for {fname_page_md}**:\n\n {str(ex)}\n\n"

                with open(pname_page_md, "w", encoding="utf-8") as f:
                    f.write(md_page)
            fnames_page_md_gen.append(fname_page_md)

        if not is_in_repair_mode(md_info):
            fnames_imgs.extend(fname_rect_images)
            fnames_snps.append(fname_page_name)
            pnames_page_md.append(pname_page_md[len(output_dir) + 1 :])
    logging.info(
        f"GITM: pages have been generated: {fnames_page_md_gen} from images is_in_repair_mode: {is_in_repair_mode(md_info)}"
    )

    if not is_in_repair_mode(md_info):
        md_info[MIFN.FNAMES_MD_PAGES] = pnames_page_md
        md_info[MIFN.FNAMES_IMGS] = fnames_imgs
        md_info[MIFN.FNAMES_SNPS] = fnames_snps
        md_info.save()


if __name__ == "__main__":
    setup_logger_handlers()
