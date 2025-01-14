import os
import sys
import types
import logging
from logging.handlers import TimedRotatingFileHandler

import colorlog
from dotenv import find_dotenv, load_dotenv

load_dotenv()

MODULE_NAME = "__global_logging_state__"

# 如果该模块未被创建过则创建
if MODULE_NAME not in sys.modules:
    # 创建一个全新的模块对象
    global_state_module = types.ModuleType(MODULE_NAME)
    # 在模块对象上挂载需要的全局状态变量
    global_state_module.initialized = False
    global_state_module.handlers_added = False
    global_state_module.log_level = "INFO"

    # 将此虚拟模块对象注册到 sys.modules 中
    sys.modules[MODULE_NAME] = global_state_module

global_state_module.g_logger_inited = False
global_state_module.g_hooked_logger_names = []
global_state_module.g_stdout_handler = None
global_state_module.g_main_handler = None
global_state_module.g_error_handler = None
global_state_module.g_progress_handler = None

_LOGGER_NAME_LLM = "llm_call"
_LOGGER_NAME_PRG = "app_gradio"


def get_logger_llm():
    logger_llm = logging.getLogger(_LOGGER_NAME_LLM)
    logger_llm.propagate = False
    return logger_llm


def get_logger_progress():
    logger_prg = logging.getLogger(_LOGGER_NAME_PRG)
    logger_prg.propagate = False
    return logger_prg


def _get_log_dir():
    log_dir = os.path.abspath(os.path.dirname(find_dotenv()))
    log_dir = os.path.join(log_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    return log_dir


def _get_log_prefix():
    return os.environ.get("APP_LOG_PREFIX", "ctn2md")


def _get_log_pathname_main():
    log_dir = _get_log_dir()
    srs_name = f"{_get_log_prefix()}.log"
    log_srs_file = os.path.join(log_dir, srs_name)
    return log_srs_file


def _get_log_pathname_error():
    log_dir = _get_log_dir()
    sre_name = f"{_get_log_prefix()}_error.log"
    log_sre_file = os.path.join(log_dir, sre_name)
    return log_sre_file


def _get_log_pathname_llm():
    log_dir = _get_log_dir()
    srs_name = f"{_get_log_prefix()}_llm.log"
    log_srl_file = os.path.join(log_dir, srs_name)
    return log_srl_file


def _get_log_pathname_progress():
    log_dir = _get_log_dir()
    srs_name = f"{_get_log_prefix()}_prg.log"
    log_srp_file = os.path.join(log_dir, srs_name)
    return log_srp_file


def _get_handler_stdout():
    if global_state_module.g_stdout_handler is not None:
        return global_state_module.g_stdout_handler

    global_state_module.g_stdout_handler = logging.StreamHandler(sys.stdout)
    formatter = colorlog.ColoredFormatter(
        "%(log_color)s %(asctime)s %(process)d %(levelname)-8s%(reset)s %(blue)s%(message)s",
        datefmt=None,
        reset=True,
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        },
        secondary_log_colors={},
        style="%",
    )
    # formatter = logging.Formatter('%(asctime)s - PID:%(process)d - %(levelname)s - %(message)s')
    global_state_module.g_stdout_handler.setFormatter(formatter)
    global_state_module.g_stdout_handler.setLevel(logging.DEBUG)  # 为handler设置级别
    return global_state_module.g_stdout_handler


def _get_handler_main():
    if global_state_module.g_main_handler is not None:
        return global_state_module.g_main_handler

    log_srs_file = _get_log_pathname_main()
    global_state_module.g_main_handler = TimedRotatingFileHandler(
        log_srs_file,
        when="midnight",
        interval=1,
        backupCount=30,
        delay=True,
        encoding="utf-8",
    )
    global_state_module.g_main_handler.suffix = "%Y-%m-%d.log"
    formatter = logging.Formatter(
        "%(asctime)s - PID:%(process)d - %(levelname)s - %(message)s"
    )
    global_state_module.g_main_handler.setFormatter(formatter)
    global_state_module.g_main_handler.setLevel(logging.INFO)  # 为handler设置级别
    return global_state_module.g_main_handler


def _get_handler_error():
    if global_state_module.g_error_handler is not None:
        return global_state_module.g_error_handler

    log_sre_file = _get_log_pathname_error()
    global_state_module.g_error_handler = TimedRotatingFileHandler(
        log_sre_file,
        when="midnight",
        interval=7,
        backupCount=30,
        delay=True,
        encoding="utf-8",
    )
    global_state_module.g_error_handler.suffix = "%Y-%m-%d.log"
    formatter = logging.Formatter(
        "%(asctime)s - PID:%(process)d - %(levelname)s - %(message)s"
    )
    global_state_module.g_error_handler.setFormatter(formatter)
    global_state_module.g_error_handler.setLevel(logging.ERROR)  # 为handler设置级别
    return global_state_module.g_error_handler


def _get_handler_progress():
    if global_state_module.g_progress_handler is not None:
        return global_state_module.g_progress_handler

    log_srp_file = _get_log_pathname_progress()
    global_state_module.g_progress_handler = TimedRotatingFileHandler(
        log_srp_file,
        when="midnight",
        interval=1,
        backupCount=30,
        delay=True,
        encoding="utf-8",
    )
    global_state_module.g_progress_handler.suffix = "%Y-%m-%d.log"
    formatter = logging.Formatter(
        "%(asctime)s - PID:%(process)d - %(levelname)s - %(message)s"
    )
    global_state_module.g_progress_handler.setFormatter(formatter)
    global_state_module.g_progress_handler.setLevel(logging.INFO)  # 为handler设置级别
    return global_state_module.g_progress_handler


def hook_handlers(logger):
    if logger is None:
        return

    if not hasattr(logger, "name"):
        return

    if logger.name in global_state_module.g_hooked_logger_names:
        return

    logger.propagate = False
    logger.handlers = (
        []
    )  # clear up default handler (likely stdout), as we have ourown hanlder

    global_state_module.g_hooked_logger_names.append(logger.name)
    # print(f"logger {logger.name} hooked")

    handlder_stdout = _get_handler_stdout()
    if handlder_stdout not in logger.handlers:
        logger.addHandler(handlder_stdout)

    handler_main = _get_handler_main()
    if handler_main not in logger.handlers:
        logger.addHandler(handler_main)

    handler_error = _get_handler_error()
    if handler_error not in logger.handlers:
        logger.addHandler(handler_error)


def _setup_logger_llm():
    logger_llm = logging.getLogger(_LOGGER_NAME_LLM)
    logger_llm.propagate = False

    log_srl_file = _get_log_pathname_llm()
    srl_handler = TimedRotatingFileHandler(
        log_srl_file,
        when="midnight",
        interval=1,
        backupCount=30,
        delay=True,
        encoding="utf-8",
    )
    srl_handler.suffix = "%Y-%m-%d.log"
    formatter = logging.Formatter(
        "%(asctime)s - PID:%(process)d - %(levelname)s - %(message)s"
    )
    srl_handler.setFormatter(formatter)
    srl_handler.setLevel(logging.DEBUG)  # 为handler设置级别
    logger_llm.addHandler(srl_handler)


def _setup_logger_prg():
    logger_prg = logging.getLogger(_LOGGER_NAME_PRG)
    logger_prg.propagate = False

    log_srg_file = _get_log_pathname_progress()
    srl_handler = TimedRotatingFileHandler(
        log_srg_file,
        when="midnight",
        interval=1,
        backupCount=30,
        delay=True,
        encoding="utf-8",
    )
    srl_handler.suffix = "%Y-%m-%d.log"
    formatter = logging.Formatter(
        "%(asctime)s - PID:%(process)d - %(levelname)s - %(message)s"
    )
    srl_handler.setFormatter(formatter)
    srl_handler.setLevel(logging.DEBUG)  # 为handler设置级别
    logger_prg.addHandler(srl_handler)


def setup_logger_handlers(level=logging.INFO):
    if global_state_module.g_logger_inited:
        return
    global_state_module.g_logger_inited = True

    logging.basicConfig(level=level)
    logging.getLogger().setLevel(level=level)

    # hook logging to output the log to stdout as well
    logger = logging.getLogger()
    hook_handlers(logger)

    logger = logging.getLogger("openai")
    hook_handlers(logger)

    logger = logging.getLogger("httpx")
    hook_handlers(logger)

    os.environ["OPENAI_LOG"] = "debug"
    _setup_logger_llm()
    _setup_logger_prg()


def _move_log_files(log_filename):
    import shutil

    try:
        log_filename_bak = log_filename + ".bak"
        if os.path.isfile(log_filename_bak):
            os.unlink(log_filename_bak)

        if os.path.isfile(log_filename):
            shutil.copy(log_filename, log_filename_bak)
            logging.info(f"MLF: moving {log_filename} to {log_filename_bak}")
            if os.path.isfile(log_filename):
                os.unlink(log_filename)

    except Exception as ex:
        logging.exception(str(ex))


def reset_log_files():
    logging.info("RLF: move log (srs, sre) files")
    log_srs_file = _get_log_pathname_main()
    _move_log_files(log_srs_file)

    log_sre_file = _get_log_pathname_error()
    _move_log_files(log_sre_file)
    logging.info("RLF: move log (srs, sre) done")


if __name__ == "__main__":
    setup_logger_handlers()
    logging.debug("HELLO ERROR")
    logging.info("HELLO INFO")
    logging.error("HELLO ERROR")
