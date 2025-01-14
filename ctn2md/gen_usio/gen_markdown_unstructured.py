import os

#TODO: ethan_pending hook unstructure_io， the benifit of using unstructured_io is that you are able to setup environment locally.
def generate_markdown_unstructured(md_info):
    doc_pathname = md_info.get_doc_pathname()
    if (doc_pathname is None) or (not os.path.isfile(doc_pathname)):
        raise ValueError(f"doc_pathname is not valid {doc_pathname}")

    raise ValueError("not implemented yet")