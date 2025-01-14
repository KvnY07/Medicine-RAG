class CTN_TYPE:
    PDF = "PDF"
    PPT = "PPT"
    DOC = "DOC"
    XLS = "XLS"
    MD = "MD"

    AUTO = "AUTO"
    UNKNOWN = "UNKNOWN"

    @classmethod
    def get_ctn_type_by_doc_type(cls, doc_type):
        if isinstance(doc_type, str):
            doc_type = doc_type.replace(".", "")
            doc_type = doc_type.lower()
            if doc_type in ["pdf"]:
                return cls.PDF
            elif doc_type in ["ppt", "pptx"]:
                return cls.PPT
            elif doc_type in ["doc", "docx"]:
                return cls.DOC
            elif doc_type in ["xls", "xlsx"]:
                return cls.XLS
            elif doc_type in ["md"]:
                return cls.MD
        
        return cls.UNKNOWN

    @classmethod
    def get_ctn_type_by_doc_pathname(cls, doc_pathname):
        ext_name = doc_pathname.split(".")[-1]
        return cls.get_ctn_type_by_doc_type(ext_name)


    