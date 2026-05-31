# 文件尾附加数据 / 嵌入文件分析脚本
# 检测图片结构结束后附加的数据，并扫描内部嵌入的其它文件（binwalk 简化版）
import sys
import os
import re
import binascii

# 统一以 UTF-8 输出，避免在中文 Windows 控制台/管道下 emoji 触发 GBK 编码错误
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# 常见文件签名（魔数）-> 描述
SIGNATURES = [
    (b'\x89PNG\r\n\x1a\n', 'PNG 图片'),
    (b'\xff\xd8\xff', 'JPEG 图片'),
    (b'GIF87a', 'GIF 图片'),
    (b'GIF89a', 'GIF 图片'),
    (b'BM', 'BMP 图片'),
    (b'PK\x03\x04', 'ZIP / Office / JAR'),
    (b'PK\x05\x06', 'ZIP 空档案尾'),
    (b'Rar!\x1a\x07', 'RAR 压缩包'),
    (b'7z\xbc\xaf\x27\x1c', '7z 压缩包'),
    (b'\x1f\x8b\x08', 'GZIP 压缩包'),
    (b'\x42\x5a\x68', 'BZIP2 压缩包'),
    (b'%PDF', 'PDF 文档'),
    (b'\x52\x49\x46\x46', 'RIFF (WAV/AVI/WEBP)'),
    (b'\x49\x44\x33', 'MP3 (ID3)'),
    (b'\xff\xfb', 'MP3'),
    (b'\x4d\x5a', 'Windows PE/EXE'),
]

FLAG_REGEX = re.compile(rb'[A-Za-z0-9_]{1,32}\{[^{}\n]{1,256}\}')


def find_structural_end(data):
    """返回图片结构正常结束的偏移；无法判定时返回 None"""
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        idx = data.rfind(b'IEND')
        if idx != -1:
            return idx + 8  # IEND + 4 字节 CRC
    elif data.startswith(b'\xff\xd8'):
        idx = data.rfind(b'\xff\xd9')
        if idx != -1:
            return idx + 2
    elif data.startswith((b'GIF87a', b'GIF89a')):
        idx = data.rfind(b'\x3b')
        if idx != -1:
            return idx + 1
    return None


def hexdump(data, length=64):
    chunk = data[:length]
    hex_part = binascii.hexlify(chunk).decode()
    hex_part = ' '.join(hex_part[i:i + 2] for i in range(0, len(hex_part), 2))
    ascii_part = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in chunk)
    return hex_part, ascii_part


def analyze_appended_data(image_path):
    result = f"📁 文件尾 / 嵌入文件分析: {os.path.basename(image_path)}\n"
    result += "=" * 60 + "\n"

    with open(image_path, 'rb') as f:
        data = f.read()

    result += f"文件总大小: {len(data)} 字节\n\n"

    # 1. 结构结束后的附加数据
    end = find_structural_end(data)
    if end is None:
        result += "⚠️  无法判定图片结构结束位置（非 PNG/JPEG/GIF 或格式异常）\n"
    elif end >= len(data):
        result += "✅ 图片结构结束于文件末尾，无尾部附加数据\n"
    else:
        trailing = data[end:]
        result += f"🚨 检测到尾部附加数据: 偏移 {end}，长度 {len(trailing)} 字节\n"
        hex_part, ascii_part = hexdump(trailing)
        result += f"  HEX : {hex_part}\n"
        result += f"  ASCII: {ascii_part}\n"

        # 识别附加数据的类型
        for sig, desc in SIGNATURES:
            if trailing.startswith(sig):
                result += f"  📦 附加数据疑似: {desc}\n"
                break

        out_name = f"appended_from_{os.path.splitext(os.path.basename(image_path))[0]}.bin"
        with open(out_name, 'wb') as f:
            f.write(trailing)
        result += f"  💾 已保存附加数据: {out_name}\n"

    # 2. 全文件签名扫描（跳过偏移 0 的本体签名）
    result += "\n🔍 嵌入文件签名扫描:\n"
    found = []
    for sig, desc in SIGNATURES:
        start = 1
        while True:
            idx = data.find(sig, start)
            if idx == -1:
                break
            found.append((idx, desc))
            start = idx + 1
    if found:
        for idx, desc in sorted(found)[:30]:
            result += f"  偏移 {idx:>10}: {desc}\n"
        if len(found) > 30:
            result += f"  ... 共 {len(found)} 处，仅显示前 30 处\n"
    else:
        result += "  未发现额外嵌入文件签名\n"

    # 3. flag 扫描
    result += "\n🚩 Flag 扫描:\n"
    flags = list(dict.fromkeys(FLAG_REGEX.findall(data)))
    if flags:
        for flag in flags[:10]:
            result += f"  {flag.decode('latin-1')}\n"
    else:
        result += "  未在原始字节中发现 flag{...} 模式\n"

    return result


if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            print(analyze_appended_data(sys.argv[1]))
        except FileNotFoundError:
            print(f"❌ 文件不存在: {sys.argv[1]}")
        except Exception as e:
            print(f"❌ 分析出错: {e}")
    else:
        print("❌ 请提供图片路径作为参数")
        print("使用方法: python file_append.py <图片路径>")
