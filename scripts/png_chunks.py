# PNG 区块与文本块分析脚本
# 列出 PNG 所有区块并解码 tEXt/zTXt/iTXt 文本块，常用于发现隐藏的备注或 flag
import sys
import os
import re
import struct
import zlib

# 统一以 UTF-8 输出，避免在中文 Windows 控制台/管道下 emoji 触发 GBK 编码错误
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

FLAG_REGEX = re.compile(r'[A-Za-z0-9_]{1,32}\{[^{}\n]{1,256}\}')


def decode_text_chunk(chunk_type, data):
    """解码 tEXt/zTXt/iTXt，返回 (keyword, text) 或 None"""
    try:
        if chunk_type == 'tEXt':
            keyword, text = data.split(b'\x00', 1)
            return keyword.decode('latin-1'), text.decode('latin-1')
        if chunk_type == 'zTXt':
            keyword, rest = data.split(b'\x00', 1)
            # rest[0] 为压缩方法，其后为 zlib 压缩数据
            text = zlib.decompress(rest[1:]).decode('latin-1')
            return keyword.decode('latin-1'), text
        if chunk_type == 'iTXt':
            keyword, rest = data.split(b'\x00', 1)
            compression_flag = rest[0]
            # rest[1] 压缩方法，随后 语言标签\0 翻译关键字\0 文本
            parts = rest[3:].split(b'\x00', 2)
            if len(parts) == 3:
                text_bytes = parts[2]
                if compression_flag == 1:
                    text_bytes = zlib.decompress(text_bytes)
                return keyword.decode('latin-1'), text_bytes.decode('utf-8', 'ignore')
    except Exception as e:
        return f'<解码失败>', str(e)
    return None


def analyze_png_chunks(image_path):
    result = f"📁 PNG 区块分析: {os.path.basename(image_path)}\n"
    result += "=" * 60 + "\n"

    with open(image_path, 'rb') as f:
        data = f.read()

    if not data.startswith(b'\x89PNG\r\n\x1a\n'):
        return result + "❌ 不是有效的 PNG 文件\n"

    pos = 8
    chunk_count = 0
    text_chunks = []
    all_text = []

    result += "区块列表 (类型  长度  CRC):\n"
    while pos + 8 <= len(data):
        length = struct.unpack('>I', data[pos:pos + 4])[0]
        chunk_type = data[pos + 4:pos + 8].decode('latin-1', 'ignore')
        chunk_data = data[pos + 8:pos + 8 + length]
        crc_stored = data[pos + 8 + length:pos + 12 + length]

        crc_calc = struct.pack('>I', zlib.crc32(data[pos + 4:pos + 8 + length]) & 0xffffffff)
        crc_ok = "OK" if crc_stored == crc_calc else "❌ 不匹配"
        result += f"  {chunk_type:<6} {length:>8}  {crc_ok}\n"

        if chunk_type in ('tEXt', 'zTXt', 'iTXt'):
            decoded = decode_text_chunk(chunk_type, chunk_data)
            if decoded:
                text_chunks.append((chunk_type, decoded[0], decoded[1]))
                all_text.append(decoded[1])

        chunk_count += 1
        if chunk_type == 'IEND':
            break
        pos += 12 + length

    result += f"\n共 {chunk_count} 个区块\n"

    # IHDR 基本信息
    if data[12:16] == b'IHDR':
        w, h, bit_depth, color_type = struct.unpack('>IIBB', data[16:26])
        result += f"\n图像信息: {w}x{h}, 位深 {bit_depth}, 颜色类型 {color_type}\n"

    # 文本块内容
    result += "\n📝 文本块内容:\n"
    if text_chunks:
        for ctype, keyword, text in text_chunks:
            result += f"  [{ctype}] {keyword}: {text}\n"
    else:
        result += "  未发现 tEXt/zTXt/iTXt 文本块\n"

    # flag 扫描
    result += "\n🚩 Flag 扫描:\n"
    flags = list(dict.fromkeys(FLAG_REGEX.findall("\n".join(all_text))))
    if flags:
        for flag in flags:
            result += f"  {flag}\n"
    else:
        result += "  未在文本块中发现 flag{...} 模式\n"

    return result


if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            print(analyze_png_chunks(sys.argv[1]))
        except FileNotFoundError:
            print(f"❌ 文件不存在: {sys.argv[1]}")
        except Exception as e:
            print(f"❌ 分析出错: {e}")
    else:
        print("❌ 请提供图片路径作为参数")
        print("使用方法: python png_chunks.py <图片路径>")
