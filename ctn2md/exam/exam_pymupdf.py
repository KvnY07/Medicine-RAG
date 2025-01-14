import fitz  # PyMuPDF
import os
import rich
import sys 
import logging
from dotenv import load_dotenv

load_dotenv()
if './' not in sys.path:
    sys.path.append('./')

from ctn2md.utils.util_logging import setup_logger_handlers

dimlimit = 100  # each image side must be greater than this
relsize = 0.05  # image : pixmap size ratio must be larger than this (5%)
abssize = 2048  # absolute image size limit 2 KB: ignore if smaller
#imgdir = "output"  # found images are stored here

def recoverpix(doc, x, imgdict):
    """Return pixmap for item with an image mask."""
    s = imgdict["smask"]  # xref of its image mask

    try:
        pix0 = fitz.Pixmap(imgdict["image"])
        mask = fitz.Pixmap(doc.extract_image(s)["image"])
        pix = fitz.Pixmap(pix0, mask)
        if pix0.n > 3:
            ext = "pam"
        else:
            ext = "png"
        return {"ext": ext, "colorspace": pix.colorspace.n, "image": pix.tobytes(ext)}
    except Exception as ex:
        logging.exception(ex)
        return None

def _dump_img_t0(doc, output_dir):
    cnt = 0
    # images = doc.get_images()
    # for ndx, image in enumerate(images):
    #     xref = image[0]
    #     pix = fitz.Pixmap(doc, xref)
    #     try:
    #         if pix.n < 5:  # 这是 GRAY 或 RGB
    #             pix.save(f"{output_dir}/t00_page{current_page}-{ndx}-{xref}.png")
    #         else:  # CMYK: 先转换为 RGB
    #             pix1 = fitz.Pixmap(fitz.csRGB, pix)
    #             pix1.save(f"{output_dir}/t01_page{current_page}-{ndx}-{xref}.png")
    #             pix1 = None
    #         cnt += 1
    #         pix = None
    #     except Exception as ex:
    #         logging.exception(ex)
    return cnt    

def _dump_img_t1(doc, output_dir):
    cnt = 0
    for current_page in range(len(doc)):
        images = doc.get_page_images(current_page, full=True)
        for ndx, image in enumerate(images):
            xref = image[0]
            pix = fitz.Pixmap(doc, xref)
            try:
                if pix.n < 5:  # 这是 GRAY 或 RGB
                    pix.save(f"{output_dir}/t10_page{current_page}-{ndx}-{xref}.png")
                else:  # CMYK: 先转换为 RGB
                    pix1 = fitz.Pixmap(fitz.csRGB, pix)
                    pix1.save(f"{output_dir}/t11_page{current_page}-{ndx}-{xref}.png")
                    pix1 = None
                cnt += 1
                pix = None
            except Exception as ex:
                logging.exception(ex)
    return cnt

def _dump_img_t2(doc, output_dir):
    cnt = 0
    for current_page in range(len(doc)):
        pixmap = doc.get_page_pixmap(current_page)
        if pixmap is not None:
            pixmap.save(f"{output_dir}/t2_page{current_page}-page.png")
            cnt += 1
    return cnt

def _dump_img_t3(doc, output_dir):
    img_ocnt = 0
    img_icnt = 0
    smasks = set()  # stores xrefs of /SMask objects
    lenXREF = doc.xref_length()  # PDF object count - do not use entry 0!
    for xref in range(1, lenXREF):  # scan through all PDF objects
        if doc.xref_get_key(xref, "Subtype")[1] != "/Image":  # not an image
            continue
        if xref in smasks:  # ignore smask
            continue

        imgdict = doc.extract_image(xref)

        if not imgdict:  # not an image
            continue

        img_icnt += 1  # increase read images counter

        smask = imgdict["smask"]
        if smask > 0:  # store /SMask xref
            smasks.add(smask)

        width = imgdict["width"]
        height = imgdict["height"]
        ext = imgdict["ext"]

        #if min(width, height) <= dimlimit:  # rectangle edges too small
        #    continue

        imgdata = imgdict["image"]  # image data
        l_imgdata = len(imgdata)  # length of data
        # if l_imgdata <= abssize:  # image too small to be relevant
        #     continue

        if smask > 0:  # has smask: need use pixmaps
            imgdict = recoverpix(doc, xref, imgdict)  # create pix with mask applied
            if imgdict is None:  # something went wrong
                continue
            ext = "png"
            imgdata = imgdict["image"]
            l_samples = width * height * 3
            l_imgdata = len(imgdata)
        else:
            c_space = max(1, imgdict["colorspace"])  # get the colorspace n
            l_samples = width * height * c_space  # simulated samples size

        if l_imgdata / l_samples <= relsize:  # seems to be unicolor image
            continue

        # now we have an image worthwhile dealing with
        img_ocnt += 1

        imgn1 = "t3_img-%i.%s" % (xref, ext)
        imgname = os.path.join(output_dir, imgn1)
        ofile = open(imgname, "wb")
        ofile.write(imgdata)
        ofile.close()
    return img_ocnt

def scan_images_from_pdf(pdf_document):
    output_dir = "_work/fitz"
    os.makedirs(output_dir, exist_ok=True)

    doc = fitz.open(pdf_document)
    rich.print(doc)

    cnt0 = _dump_img_t0(doc, output_dir)
    cnt1 = _dump_img_t1(doc, output_dir)
    cnt2 = _dump_img_t2(doc, output_dir)
    cnt3 = _dump_img_t3(doc, output_dir)
    print(cnt0, cnt1, cnt2, cnt3)

if __name__ == "__main__":
    setup_logger_handlers()

    #doc_pathname = "datasrc/exam/raw_docs/深度学习在视电阻率快速反演中的研究.pdf"
    #doc_pathname = "datasrc/exam/raw_docs/DIFFERENTIAL TRANSFORMER 2410.05258v1.pdf"
    doc_pathname = "datasrc/exam/raw_docs/Winning Solution For Meta KDD Cup’ 24 2410.00005v1.pdf"

    scan_images_from_pdf(doc_pathname)