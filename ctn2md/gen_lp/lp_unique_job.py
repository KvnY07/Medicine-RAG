from dotenv import load_dotenv
import os
import sys
import logging
#import rich
#import random
#import re
import shutil

load_dotenv()

if "./" not in sys.path:
    sys.path.append("./")

#from ctn2md.src.md_info_base import MIFN

def n2u_replace_fnames(md_info, mifn_fnames, unique_job_id, new_job_id):
    out_dir = md_info.get_out_dir()
    changed = 0
    md_info_mifn_fnames = md_info[mifn_fnames]
    for ndx, new_fname in enumerate(md_info_mifn_fnames):
        unique_fname = new_fname.replace(new_job_id, unique_job_id)
        if unique_fname != new_fname:

            src_fname = os.path.join(out_dir, new_fname)
            dst_fname = os.path.join(out_dir, unique_fname)
            
            if os.path.isfile(src_fname):
                if os.path.isfile(dst_fname):
                    os.unlink(dst_fname)
                shutil.move(src_fname, dst_fname)
                md_info_mifn_fnames[ndx] = unique_fname
            else:
                if not os.path.isfile(dst_fname):
                    logging.error(f"NRF: {src_fname} not exist? and {dst_fname} not exist")
                else:
                    logging.error(f"NRF: {src_fname} not exist")
            changed += 1
    return changed

def n2u_update_md_content(md_info, pathname_md, unique_job_id, new_job_id):
    with open(pathname_md, "r") as f: 
        md_text = f.read()

    with open(pathname_md, "w+") as f: 
        md_text_new = md_text.replace(new_job_id, unique_job_id)
        f.write(md_text_new)
