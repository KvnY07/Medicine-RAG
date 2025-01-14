import os
import sys

# import random
# import re
import shutil
import logging

import rich
from dotenv import load_dotenv

load_dotenv()

if "./" not in sys.path:
    sys.path.append("./")

from ctn2md.src.md_info_base import MIFN, FHL_QUALITY_TYPE, MdInfo
from ctn2md.utils.util_logging import setup_logger_handlers
from ctn2md.utils.util_ctn_type import CTN_TYPE
from ctn2md.utils.util_markdown import find_all_image_refs
from ctn2md.src.ctn2md_gen_md_base import GenMd_Base


def _copy_img_files_in_markdown(doc_pathname, out_dir):
    """
    Scans the Markdown file for image references, copies the images from `src_dir` to `out_dir`.

    :param doc_pathname: Path to the Markdown file
    :param out_dir: Output directory where images will be copied
    """
    # Get the source directory of the Markdown file
    src_dir = os.path.dirname(doc_pathname)

    # Ensure the output directory exists
    os.makedirs(out_dir, exist_ok=True)

    image_refs = find_all_image_refs(doc_pathname)

    # Process each image reference
    for ref_url in image_refs:
        # Resolve the full source path of the image
        src_path = os.path.join(src_dir, ref_url)

        # If the source path exists, copy it to the output directory
        if os.path.exists(src_path):
            # Compute the destination path
            dest_path = os.path.join(out_dir, ref_url)

            # Create directories for the destination path if necessary
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)

            # Copy the file
            shutil.copy2(src_path, dest_path)
            logging.info(f"Copied: {src_path} -> {dest_path}")
        else:
            logging.info(f"Warning: File not found - {src_path}")
    return image_refs


def _gen_md_plain(doc_pathname, md_info):
    logging.info(f"##MDFLOW##: gen_md_plain started...")

    out_dir = md_info.get_out_dir()
    md_info.set_gen_engine("md2md:plain")
    md_info.set_doc_pathname(doc_pathname)
    md_info[MIFN.FHL_QUALITY] = FHL_QUALITY_TYPE.LOW

    pathname_final_md = md_info.name_step_pathname(-1)
    if pathname_final_md == doc_pathname:
        raise ValueError(f"src_md cannot be same as dst_md: {doc_pathname}")
    pathname_s0_md = md_info.name_step_pathname(0)
    shutil.copy(doc_pathname, pathname_s0_md)
    logging.info(f"copy md from {doc_pathname} to {pathname_s0_md}")
    md_info.add_step_into_md_info_mdflow(pathname_s0_md, actor="gen_md_plain")
    md_info.save()

    img_refs = _copy_img_files_in_markdown(doc_pathname, out_dir)
    md_info[MIFN.FNAMES_IMGS] = img_refs
    md_info.save()

    md_info_path = md_info.get_md_info_path()

    logging.info(f"##MDFLOW##: gen_md_plain end")
    return md_info_path


class GenMd_Plain(GenMd_Base):
    SUPPORT_CNT_TYPES = [CTN_TYPE.MD]
    OD_SUFFIX = "md"

    @classmethod
    def generate_markdown(
        cls, doc_pathname, out_dir=None, enforced_gen=False, mdcontrols=None
    ):
        if not cls.does_support_doc_type(doc_pathname):
            raise ValueError(f"GenMd_Plain does not support '{doc_pathname}'")

        md_info, gen_needed = cls.does_gen_needed(doc_pathname, out_dir, enforced_gen)

        if isinstance(mdcontrols, dict):
            md_info.update_mdcontrols(mdcontrols)
            md_info.save()

        if gen_needed:
            md_info_path = _gen_md_plain(doc_pathname, md_info)
            if md_info_path is None:
                return None

        return md_info.get_md_info_path()


if __name__ == "__main__":
    # doc_pathname = "_output/ctn2md_attention_is_all_you_need/attention_is_all_you_need___pdf_s0.md"
    doc_pathname = (
        "_output/ctn2md_attention_is_all_you_need/attention_is_all_you_need___pdf.md"
    )

    out_dir = MdInfo.get_suggested_out_dir(doc_pathname, GenMd_Plain.OD_SUFFIX)
    md_info = MdInfo(out_dir)

    setup_logger_handlers()
    os.makedirs(out_dir, exist_ok=True)
    md_info_path = GenMd_Plain.generate_markdown(doc_pathname, out_dir=out_dir)
    print(md_info_path)

    md_info = MdInfo(md_info_path)
    rich.print(md_info)
    print(md_info_path)
