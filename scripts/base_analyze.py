# CTF图片分析脚本
import sys
from PIL import Image
import binascii
import os

def analyze_ctf_image(image_path):
    """分析CTF图片中的隐藏信息"""
    try:
        img = Image.open(image_path)

        result = "CTF图片分析结果:\n"
        result += f"图片尺寸: {img.size}\n"
        result += f"图片模式: {img.mode}\n"
        result += f"图片格式: {img.format}\n"

        # 检查可能的LSB隐写（取前100像素）
        rgb = img.convert('RGB')
        w, h = rgb.size
        count = min(100, w * h)
        if count > 0:
            lsb_string = ""
            for i in range(count):
                r, g, b = rgb.getpixel((i % w, i // w))
                lsb_string += str(r & 1) + str(g & 1) + str(b & 1)

            result += f"前100像素LSB: {lsb_string[:30]}...\n"

        # 检查文件尾
        with open(image_path, 'rb') as f:
            f.seek(-100, 2)  # 从文件末尾向前100字节
            tail_data = f.read(100)

        if tail_data.strip(b'\x00'):
            hex_data = binascii.hexlify(tail_data).decode('utf-8')
            result += f"文件尾数据(hex): {hex_data}\n"

        return result
    except Exception as e:
        return f"错误: {str(e)}"

if __name__ == "__main__":
    if len(sys.argv) > 1:
        result = analyze_ctf_image(sys.argv[1])
        print(result)
