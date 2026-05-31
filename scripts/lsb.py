# LSB隐写分析脚本
# 此脚本用于分析图片中的LSB（最低有效位）隐写信息
from PIL import Image
import sys
import os
import binascii
import struct
import re

# 统一以 UTF-8 输出，避免在中文 Windows 控制台/管道下 emoji 触发 GBK 编码错误
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def extract_lsb_from_image(img_path, method="all_channels"):
    """
    从图片中提取LSB（最低有效位）信息

    Args:
        img_path: 图片路径
        method: 提取方法，可选值:
            - "all_channels": 提取所有RGB通道的LSB
            - "red_channel": 只提取红色通道的LSB
            - "green_channel": 只提取绿色通道的LSB
            - "blue_channel": 只提取蓝色通道的LSB
    """
    try:
        img = Image.open(img_path)

        # 确保图片是RGB模式
        if img.mode != 'RGB':
            img = img.convert('RGB')

        width, height = img.size
        extracted_bits = []

        # 提取LSB
        for y in range(height):
            for x in range(width):
                pixel = img.getpixel((x, y))
                r, g, b = pixel[:3]

                if method == "all_channels":
                    # 提取所有通道的LSB
                    extracted_bits.append(str(r & 1))
                    extracted_bits.append(str(g & 1))
                    extracted_bits.append(str(b & 1))
                elif method == "red_channel":
                    extracted_bits.append(str(r & 1))
                elif method == "green_channel":
                    extracted_bits.append(str(g & 1))
                elif method == "blue_channel":
                    extracted_bits.append(str(b & 1))

        return ''.join(extracted_bits)

    except Exception as e:
        return f"❌ 提取LSB时出错: {str(e)}"


def binary_to_ascii(binary_string):
    """将二进制字符串转换为ASCII文本"""
    ascii_text = ""
    # 每8位二进制转换成一个字节
    for i in range(0, len(binary_string) - 7, 8):
        byte_str = binary_string[i:i + 8]
        try:
            char_code = int(byte_str, 2)
            if 32 <= char_code <= 126:  # 可打印ASCII字符
                ascii_text += chr(char_code)
            else:
                ascii_text += '.'  # 用点表示不可打印字符
        except:
            ascii_text += '?'

    return ascii_text


def binary_to_hex(binary_string):
    """将二进制字符串转换为十六进制"""
    hex_string = ""
    for i in range(0, len(binary_string) - 3, 4):
        nibble_str = binary_string[i:i + 4]
        try:
            hex_digit = hex(int(nibble_str, 2))[2:]
            hex_string += hex_digit
        except:
            hex_string += '?'

    return hex_string


def analyze_lsb_steganography(img_path):
    """综合LSB隐写分析"""
    try:
        result = f"🔍 LSB隐写分析报告\n"
        result += f"📁 文件: {os.path.basename(img_path)}\n"

        img = Image.open(img_path)
        width, height = img.size
        result += f"📏 尺寸: {width} x {height}\n"
        result += f"🎨 模式: {img.mode}\n"

        if img.mode != 'RGB':
            img = img.convert('RGB')
            result += f"⚠️  已转换为RGB模式进行分析\n"

        result += "-" * 60 + "\n\n"

        # 提取不同通道的LSB
        result += "📊 LSB位统计:\n"

        for method_name, method in [("所有通道", "all_channels"),
                                    ("红色通道", "red_channel"),
                                    ("绿色通道", "green_channel"),
                                    ("蓝色通道", "blue_channel")]:

            binary_data = extract_lsb_from_image(img_path, method)

            if binary_data.startswith("❌"):
                result += f"  {method_name}: {binary_data}\n"
                continue

            result += f"  {method_name}:\n"
            result += f"    二进制长度: {len(binary_data)} 位\n"

            # 统计0和1的比例
            zeros = binary_data.count('0')
            ones = binary_data.count('1')
            total = len(binary_data)

            if total > 0:
                zero_percent = zeros / total * 100
                one_percent = ones / total * 100
                result += f"    0的数量: {zeros} ({zero_percent:.1f}%)\n"
                result += f"    1的数量: {ones} ({one_percent:.1f}%)\n"

                # 检查LSB分布是否异常
                if abs(zero_percent - 50) > 20:
                    result += f"    ⚠️  LSB分布不均匀，可能包含隐藏信息\n"

            # 转换为ASCII
            ascii_text = binary_to_ascii(binary_data[:800])  # 只转换前800位
            if ascii_text and len(ascii_text.strip('.')) > 5:
                result += f"    ASCII解码: {ascii_text[:100]}...\n"

            result += "\n"

        # 高级LSB分析
        result += "🔬 高级LSB分析:\n"

        # 分析每个通道的LSB模式
        width, height = img.size
        total_pixels = width * height

        red_lsb = []
        green_lsb = []
        blue_lsb = []

        for y in range(min(100, height)):  # 只分析前100行以加快速度
            for x in range(width):
                r, g, b = img.getpixel((x, y))
                red_lsb.append(str(r & 1))
                green_lsb.append(str(g & 1))
                blue_lsb.append(str(b & 1))

        red_binary = ''.join(red_lsb)
        green_binary = ''.join(green_lsb)
        blue_binary = ''.join(blue_lsb)

        # 检查每个通道是否有规律的模式
        for channel_name, channel_bits in [("红色", red_binary),
                                           ("绿色", green_binary),
                                           ("蓝色", blue_binary)]:

            # 检查是否有明显的重复模式
            if len(channel_bits) >= 16:
                # 检查前16位是否重复
                first_8 = channel_bits[:8]
                occurrences = channel_bits.count(first_8)
                if occurrences > 5:
                    result += f"  {channel_name}通道: 发现重复模式 '{first_8}' 出现 {occurrences} 次\n"

        # 尝试检测常见的隐写工具特征
        result += "\n🛠️ 隐写工具特征检测:\n"

        # 检查是否为Steghide隐藏
        steghide_headers = ["riff", "wave", "data"]
        all_binary = extract_lsb_from_image(img_path, "all_channels")
        all_ascii = binary_to_ascii(all_binary[:800])

        for header in steghide_headers:
            if header in all_ascii.lower():
                result += f"  ✅ 可能使用Steghide隐藏文件 (检测到'{header}'头)\n"

        # 检查是否为OpenStego特征
        if "opst" in all_ascii.lower():
            result += f"  ✅ 可能使用OpenStego隐藏文件\n"

        # 检查是否为Outguess特征
        if "outguess" in all_ascii.lower():
            result += f"  ✅ 可能使用Outguess隐藏文件\n"

        # 检查常见文件头
        result += "\n📁 常见文件头检测:\n"

        # 从LSB中提取字节
        bytes_from_lsb = bytearray()
        for i in range(0, min(1000, len(all_binary) - 7), 8):
            byte_str = all_binary[i:i + 8]
            try:
                byte_val = int(byte_str, 2)
                bytes_from_lsb.append(byte_val)
            except:
                pass

        # 检查文件头
        file_headers = {
            b'\x89PNG\r\n\x1a\n': "PNG图片",
            b'\xff\xd8\xff': "JPEG图片",
            b'GIF': "GIF图片",
            b'%PDF': "PDF文档",
            b'PK': "ZIP压缩包",
            b'\x1f\x8b\x08': "GZIP压缩包",
            b'BM': "BMP图片",
            b'RIFF': "WAV音频/AVI视频",
        }

        found_headers = []
        for header, file_type in file_headers.items():
            if bytes(bytes_from_lsb[:20]).startswith(header):
                found_headers.append(file_type)

        if found_headers:
            for file_type in found_headers:
                result += f"  ✅ 检测到可能的{file_type}文件头\n"
        else:
            result += f"  ℹ️ 未检测到常见文件头\n"

        # 尝试自动提取隐藏文件
        result += "\n💾 自动提取尝试:\n"

        # 查找可能的文件边界
        if bytes_from_lsb:
            # 尝试找到ZIP文件的中央目录签名
            eocd_signature = b'PK\x05\x06'
            eocd_pos = bytes(bytes_from_lsb).find(eocd_signature)

            if eocd_pos != -1:
                result += f"  ✅ 找到ZIP文件尾签名，位置: {eocd_pos}\n"

                # 尝试提取ZIP文件
                try:
                    # 获取文件大小
                    zip_size = struct.unpack('<I', bytes_from_lsb[eocd_pos + 12:eocd_pos + 16])[0]
                    result += f"  ℹ️  ZIP文件大小: {zip_size} 字节\n"

                    if eocd_pos >= zip_size:
                        zip_start = eocd_pos - zip_size
                        zip_data = bytes_from_lsb[zip_start:eocd_pos + 22]  # 包括文件尾

                        # 保存提取的文件
                        output_name = f"extracted_from_{os.path.splitext(os.path.basename(img_path))[0]}.zip"
                        with open(output_name, 'wb') as f:
                            f.write(zip_data)

                        result += f"  💾 已提取ZIP文件: {output_name}\n"
                except:
                    result += f"  ❌ 提取ZIP文件失败\n"

        # 保存LSB数据供进一步分析
        output_base = f"lsb_data_{os.path.splitext(os.path.basename(img_path))[0]}"

        # 保存二进制数据
        with open(f"{output_base}_binary.txt", 'w') as f:
            f.write(all_binary[:10000])  # 只保存前10000位

        # 保存ASCII数据
        ascii_full = binary_to_ascii(all_binary[:10000])
        with open(f"{output_base}_ascii.txt", 'w', encoding='utf-8') as f:
            f.write(ascii_full)

        # 保存十六进制数据
        hex_data = binary_to_hex(all_binary[:10000])
        with open(f"{output_base}_hex.txt", 'w') as f:
            f.write(hex_data)

        result += f"\n💾 分析数据已保存:\n"
        result += f"  {output_base}_binary.txt (二进制数据)\n"
        result += f"  {output_base}_ascii.txt (ASCII解码)\n"
        result += f"  {output_base}_hex.txt (十六进制)\n"

        return result

    except Exception as e:
        return f"❌ LSB分析过程中出错: {str(e)}"


def extract_hidden_file_from_lsb(img_path, output_path=None):
    """尝试从LSB中提取隐藏文件"""
    try:
        img = Image.open(img_path)

        if img.mode != 'RGB':
            img = img.convert('RGB')

        width, height = img.size

        # 提取所有LSB位
        binary_data = extract_lsb_from_image(img_path, "all_channels")

        if binary_data.startswith("❌"):
            return binary_data

        # 将二进制转换为字节
        byte_data = bytearray()
        for i in range(0, len(binary_data) - 7, 8):
            byte_str = binary_data[i:i + 8]
            try:
                byte_val = int(byte_str, 2)
                byte_data.append(byte_val)
            except:
                pass

        if not output_path:
            base_name = os.path.splitext(os.path.basename(img_path))[0]
            output_path = f"hidden_from_{base_name}.bin"

        with open(output_path, 'wb') as f:
            f.write(byte_data)

        return f"✅ 已从LSB中提取 {len(byte_data)} 字节到 {output_path}"

    except Exception as e:
        return f"❌ 提取隐藏文件时出错: {str(e)}"


def search_for_patterns_in_lsb(img_path, pattern_type="flag"):
    """在LSB中搜索特定模式"""
    try:
        img = Image.open(img_path)

        if img.mode != 'RGB':
            img = img.convert('RGB')

        # 提取ASCII文本
        binary_data = extract_lsb_from_image(img_path, "all_channels")
        ascii_text = binary_to_ascii(binary_data[:10000])  # 只搜索前10000位

        result = f"🔍 在LSB中搜索 '{pattern_type}' 模式:\n"

        if pattern_type == "flag":
            # 搜索常见的flag格式
            patterns = [
                r'flag\{[^}]*\}',  # flag{...}
                r'FLAG\{[^}]*\}',  # FLAG{...}
                r'ctf\{[^}]*\}',  # ctf{...}
                r'CTF\{[^}]*\}',  # CTF{...}
                r'[A-Z0-9]{10,}',  # 大写字母和数字的组合
                r'[a-f0-9]{20,}',  # 十六进制字符串
            ]

            for pattern in patterns:
                matches = re.findall(pattern, ascii_text, re.IGNORECASE)
                if matches:
                    result += f"  匹配模式 '{pattern}':\n"
                    for match in matches[:5]:  # 只显示前5个匹配
                        result += f"    - {match}\n"

        elif pattern_type == "url":
            # 搜索URL
            url_pattern = r'https?://[^\s<>"\']+'
            matches = re.findall(url_pattern, ascii_text)
            if matches:
                result += f"  找到URL:\n"
                for match in matches[:5]:
                    result += f"    - {match}\n"

        elif pattern_type == "base64":
            # 搜索Base64编码
            base64_pattern = r'[A-Za-z0-9+/=]{20,}'
            matches = re.findall(base64_pattern, ascii_text)
            if matches:
                result += f"  找到可能的Base64编码:\n"
                for match in matches[:5]:
                    result += f"    - {match}\n"

        if "匹配" not in result and "找到" not in result:
            result += f"  未找到 '{pattern_type}' 模式\n"

        return result

    except Exception as e:
        return f"❌ 搜索模式时出错: {str(e)}"


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 获取图片路径
        img_path = sys.argv[1]

        # 执行分析
        result = analyze_lsb_steganography(img_path)
        print(result)

        # 可选：尝试提取隐藏文件
        if len(sys.argv) > 2 and sys.argv[2] == "--extract":
            extraction_result = extract_hidden_file_from_lsb(img_path)
            print(f"\n{extraction_result}")

        # 可选：搜索特定模式
        if len(sys.argv) > 2 and sys.argv[2] == "--search":
            for pattern in ["flag", "url", "base64"]:
                pattern_result = search_for_patterns_in_lsb(img_path, pattern)
                print(f"\n{pattern_result}")

    else:
        print("❌ 请提供图片路径作为参数")
        print("\n使用方法:")
        print("  python lsb_analyzer.py <图片路径>")
        print("\n可选参数:")
        print("  --extract    尝试从LSB中提取隐藏文件")
        print("  --search     在LSB中搜索常见模式 (flag, URL, base64)")
        print("\n示例:")
        print("  python lsb_analyzer.py suspicious.png")
        print("  python lsb_analyzer.py suspicious.png --extract")
        print("  python lsb_analyzer.py suspicious.png --search")