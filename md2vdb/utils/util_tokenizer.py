import logging

import rich
import tiktoken


def get_chinese_analyzer():
    from whoosh.analysis import Token, Tokenizer

    logging.info("start load jieba...")
    import jieba

    logging.info("end loading jieba")

    class _ChineseTokenizer(Tokenizer):
        def __call__(
            self,
            value,
            positions=False,
            chars=False,
            keeporiginal=False,
            removestops=True,
            start_pos=0,
            start_char=0,
            mode="",
            **kwargs
        ):

            t = Token(positions, chars, removestops=removestops, mode=mode, **kwargs)

            seglist = jieba.cut(value, cut_all=True)
            for w in seglist:
                t.original = t.text = w
                t.boost = 1.0
                if positions:
                    t.pos = start_pos + value.find(w)
                if chars:
                    t.startchar = start_char + value.find(w)
                if chars and positions:
                    t.endchar = start_char + value.find(w) + len(w)
                yield t

    return _ChineseTokenizer()


g_tk_encoding = None


def get_token_encoding():
    global g_tk_encoding
    if g_tk_encoding is None:
        embedding_encoding = "cl100k_base"
        g_tk_encoding = tiktoken.get_encoding(embedding_encoding)
    return g_tk_encoding


if __name__ == "__main__":
    import sys

    sys.path.append("./")

    from md2vdb.utils.util_logging import setup_logger_handlers

    setup_logger_handlers()

    encoding = get_token_encoding()
    rich.print(encoding)
    ret1 = encoding.encode("1, 2, 3")
    rich.print(ret1)
    ret2 = encoding.decode(ret1)
    rich.print(ret2)

    logging.info("start load tokenizer...")
    chinese_tokenizer = get_chinese_analyzer()
    logging.info("tokenizer loaded.")

    rich.print(chinese_tokenizer)

    ret3 = chinese_tokenizer("我爱北京天安门")
    rich.print(ret3)
    for token in ret3:
        print(token)

    ret3 = chinese_tokenizer("从这里来，到这里去")
    rich.print(ret3)
    for token in ret3:
        print(token)
