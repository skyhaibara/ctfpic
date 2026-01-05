# 颜色块填充脚本
# 此脚本专门处理图片中的颜色块，增强对比度以显示隐藏信息
from PIL import Image
import colorsys
import sys
import os


def find_color_block(image, x, y, visited):
    """查找相同颜色的连续块"""
    width, height = image.size
    target_color = image.getpixel((x, y))
    color_block = set()
    stack = [(x, y)]

    while stack:
        px, py = stack.pop()
        if 0 <= px < width and 0 <= py < height:
            if (px, py) not in visited and image.getpixel((px, py)) == target_color:
                color_block.add((px, py))
                visited.add((px, py))
                stack.append((px + 1, py))
                stack.append((px - 1, py))
                stack.append((px, py + 1))
                stack.append((px, py - 1))

    return color_block


def enhance_color_blocks(image_path, output_suffix="_enhanced"):
    """增强颜色块对比度"""
    try:
        image = Image.open(image_path)

        # 转换为RGB模式
        if image.mode != 'RGB':
            image = image.convert('RGB')

        width, height = image.size
        visited = set()
        color_blocks = []

        # 找到所有颜色块
        for y in range(height):
            for x in range(width):
                if (x, y) not in visited:
                    color_block = find_color_block(image, x, y, visited)
                    if len(color_block) > 1:  # 只记录大于1像素的块
                        color_blocks.append(color_block)

        # 增强颜色块
        enhanced_image = image.copy()
        enhanced_blocks = 0

        for block in color_blocks:
            if len(block) >= 4:  # 只处理足够大的块
                # 获取块的第一个像素颜色
                sample_point = next(iter(block))
                original_color = image.getpixel(sample_point)

                # 转换为HLS颜色空间
                h, l, s = colorsys.rgb_to_hls(
                    original_color[0] / 255.0,
                    original_color[1] / 255.0,
                    original_color[2] / 255.0
                )

                # 增强亮度和饱和度
                new_l = min(1.0, l + 0.3)
                new_s = min(1.0, s + 0.3)

                # 转换回RGB
                new_rgb = colorsys.hls_to_rgb(h, new_l, new_s)
                new_color = (
                    int(new_rgb[0] * 255),
                    int(new_rgb[1] * 255),
                    int(new_rgb[2] * 255)
                )

                # 填充颜色块
                for px, py in block:
                    enhanced_image.putpixel((px, py), new_color)

                enhanced_blocks += 1

        # 保存图片
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        output_path = f"{base_name}{output_suffix}.png"
        enhanced_image.save(output_path)

        result = f"✅ 颜色块增强完成:\n"
        result += f"  原始图片: {os.path.basename(image_path)}\n"
        result += f"  处理图片: {output_path}\n"
        result += f"  图片尺寸: {width} x {height}\n"
        result += f"  发现颜色块: {len(color_blocks)} 个\n"
        result += f"  增强颜色块: {enhanced_blocks} 个\n"
        result += f"  保存格式: PNG\n"

        return result

    except Exception as e:
        return f"❌ 处理过程中出错: {str(e)}\n"


if __name__ == "__main__":
    if len(sys.argv) > 1:
        result = enhance_color_blocks(sys.argv[1])
        print(result)
    else:
        print("❌ 请提供图片路径作为参数")
        print("使用方法: python color_block_filler.py <图片路径>")