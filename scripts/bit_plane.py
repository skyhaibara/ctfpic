# 位平面提取脚本
# 将各 RGB 通道的指定位平面导出为黑白图像，常用于可视化 LSB 隐写
from PIL import Image, ImageChops
import sys
import os

# 统一以 UTF-8 输出，避免在中文 Windows 控制台/管道下 emoji 触发 GBK 编码错误
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def extract_bit_planes(image_path, bits=(0,)):
    """导出各通道指定位平面，并生成各通道 LSB 合成图"""
    img = Image.open(image_path)
    if img.mode != 'RGB':
        img = img.convert('RGB')

    base = os.path.splitext(os.path.basename(image_path))[0]
    result = f"📁 位平面提取: {os.path.basename(image_path)}\n"
    result += f"📏 尺寸: {img.size[0]} x {img.size[1]}\n"
    result += "-" * 60 + "\n"

    channels = {'R': img.getchannel('R'),
                'G': img.getchannel('G'),
                'B': img.getchannel('B')}

    saved = []
    for ch_name, band in channels.items():
        for b in bits:
            # 取出第 b 位：置位则白(255)，否则黑(0)
            plane = band.point(lambda p, b=b: 255 if (p >> b) & 1 else 0)
            out_name = f"{base}_{ch_name}_bit{b}.png"
            plane.save(out_name)
            saved.append(out_name)

    # 各通道 LSB(bit0) 合成图：任一通道 LSB 为 1 即为白
    r0 = channels['R'].point(lambda p: 255 if p & 1 else 0)
    g0 = channels['G'].point(lambda p: 255 if p & 1 else 0)
    b0 = channels['B'].point(lambda p: 255 if p & 1 else 0)
    combined = ImageChops.lighter(ImageChops.lighter(r0, g0), b0)
    combined_name = f"{base}_LSB_combined.png"
    combined.save(combined_name)
    saved.append(combined_name)

    result += f"位平面: {', '.join('bit' + str(b) for b in bits)}（每通道）\n"
    result += f"💾 已导出 {len(saved)} 张图像:\n"
    for name in saved:
        result += f"  {name}\n"
    result += "\n提示: 用图片查看器打开这些图像，留意是否浮现文字/二维码等隐藏信息。\n"
    return result


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 可选: 额外参数指定要导出的位，如 "0,1,2"；默认仅 LSB(bit0)
        bits = (0,)
        if len(sys.argv) > 2:
            try:
                bits = tuple(int(x) for x in sys.argv[2].split(',') if 0 <= int(x) <= 7)
            except ValueError:
                bits = (0,)
        try:
            print(extract_bit_planes(sys.argv[1], bits))
        except FileNotFoundError:
            print(f"❌ 文件不存在: {sys.argv[1]}")
        except Exception as e:
            print(f"❌ 分析出错: {e}")
    else:
        print("❌ 请提供图片路径作为参数")
        print("使用方法: python bit_plane.py <图片路径> [位平面,如 0,1,2]")
