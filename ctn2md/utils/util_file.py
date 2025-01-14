from dotenv import load_dotenv, find_dotenv
import os
import sys

if "./" not in sys.path:
    sys.path.append("./")

load_dotenv()

def get_root_dir():
    root_dir = os.path.abspath(os.path.dirname(find_dotenv()))  
    return root_dir

def get_crc32_id(unique_str):
    import binascii
    # 将字符串转换为字节
    input_bytes = unique_str.encode('utf-8')

    # 计算CRC32校验和
    crc32_checksum = binascii.crc32(input_bytes)

    # 将CRC32校验和转换为十六进制字符串
    crc32_hex = format(crc32_checksum, '08x')  # '08x'确保输出为8个字符的十六进
    return crc32_hex