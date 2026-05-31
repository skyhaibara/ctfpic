# APNG帧延时分析脚本
# 此脚本用于分析APNG动图的帧延时信息，并提取可能的隐藏信息
import sys
import struct
import os
from pathlib import Path

# 统一以 UTF-8 输出，避免在中文 Windows 控制台/管道下 emoji 触发 GBK 编码错误
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def extract_apng_delay_info(image_path):
    """分析APNG图片的帧延时信息"""
    try:
        delay_numbers = []
        result_text = ""

        with open(image_path, 'rb') as f:
            # 检查是否为PNG文件
            header = f.read(8)
            if header != b'\x89PNG\r\n\x1a\n':
                return "错误: 不是有效的PNG文件\n"

            result_text += "✅ 文件类型: PNG/APNG\n"

            while True:
                length_bytes = f.read(4)
                if not length_bytes or len(length_bytes) < 4:
                    break

                chunk_length = struct.unpack('>I', length_bytes)[0]
                chunk_type_bytes = f.read(4)

                if not chunk_type_bytes or len(chunk_type_bytes) < 4:
                    break

                chunk_type = chunk_type_bytes.decode('ascii', errors='ignore')

                if chunk_type == 'fcTL':
                    if chunk_length != 26:
                        # 跳过不正确的fcTL块
                        f.read(chunk_length)
                        f.read(4)  # CRC
                        continue

                    chunk_data = f.read(chunk_length)
                    if len(chunk_data) < 22:
                        break

                    # 提取延时信息
                    delay_num = struct.unpack('>H', chunk_data[20:22])[0]
                    delay_numbers.append(delay_num)

                    # 提取帧序号
                    sequence_number = struct.unpack('>I', chunk_data[0:4])[0]
                    result_text += f"  帧 {sequence_number}: 延时 = {delay_num} (单位: 1/100秒)\n"

                    f.read(4)  # CRC

                elif chunk_type == 'IEND':
                    break

                else:
                    # 跳过其他块
                    f.read(chunk_length)
                    f.read(4)  # CRC

        if not delay_numbers:
            return "⚠️  未找到APNG帧延时信息 (可能是静态PNG或格式不标准)\n"

        # 分析结果
        result_text += f"\n📊 统计信息:\n"
        result_text += f"  总帧数: {len(delay_numbers)}\n"
        result_text += f"  平均延时: {sum(delay_numbers) / len(delay_numbers):.2f}\n"
        result_text += f"  最小延时: {min(delay_numbers)}\n"
        result_text += f"  最大延时: {max(delay_numbers)}\n"

        # 尝试从延时值中提取ASCII字符
        ascii_result = ""
        hex_result = ""
        decimal_values = []

        for i, num in enumerate(delay_numbers):
            if 32 <= num <= 126:  # 可打印ASCII范围
                ascii_result += chr(num)
                hex_result += f"{num:02X} "
                decimal_values.append(num)
            else:
                ascii_result += "."
                hex_result += f"{num:02X} "
                decimal_values.append(num)

        result_text += f"\n🔍 隐藏信息分析:\n"
        result_text += f"  延时值序列: {delay_numbers}\n"
        result_text += f"  十进制值: {decimal_values}\n"
        result_text += f"  十六进制: {hex_result}\n"
        result_text += f"  ASCII解码: {ascii_result}\n"

        # 尝试不同的解码方式
        result_text += f"\n🧪 其他解码尝试:\n"

        # 1. 直接转换为ASCII（忽略不可打印字符）
        ascii_filtered = ""
        for num in delay_numbers:
            if 32 <= num <= 126:
                ascii_filtered += chr(num)

        if ascii_filtered and len(ascii_filtered) > 2:
            result_text += f"  可打印ASCII: '{ascii_filtered}'\n"

        # 2. 检查是否为常见CTF格式
        # 检查是否为常见CTF标志
        possible_flags = []
        for i in range(len(delay_numbers) - 3):
            if (delay_numbers[i] == 102 and delay_numbers[i + 1] == 108 and
                    delay_numbers[i + 2] == 97 and delay_numbers[i + 3] == 103):
                possible_flags.append(i)

        if possible_flags:
            result_text += f"  检测到可能的'flag'模式在位置: {possible_flags}\n"

        # 3. 尝试Base64解码
        try:
            import base64
            # 将延时值转换为字节
            byte_values = bytes(delay_numbers)
            # 尝试base64解码
            try:
                decoded = base64.b64decode(byte_values)
                if decoded and len(decoded) > 0:
                    result_text += f"  Base64解码: {decoded[:50]}...\n"
            except:
                pass
        except ImportError:
            pass

        return result_text

    except FileNotFoundError:
        return f"❌ 文件不存在: {image_path}\n"
    except Exception as e:
        return f"❌ 分析出错: {str(e)}\n"


def analyze_apng_delay(image_path):
    """主分析函数，将被主程序调用"""
    file_name = os.path.basename(image_path)
    result = f"📁 分析文件: {file_name}\n"
    result += "=" * 50 + "\n"

    result += extract_apng_delay_info(image_path)

    result += "\n" + "=" * 50 + "\n"
    result += "✅ APNG分析完成\n"

    return result


if __name__ == "__main__":
    if len(sys.argv) > 1:
        result = analyze_apng_delay(sys.argv[1])
        print(result)
    else:
        print("❌ 请提供图片路径作为参数")
        print("使用方法: python apng_analyzer.py <图片路径>")