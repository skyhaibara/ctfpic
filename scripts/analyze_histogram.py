# 分析图片颜色直方图
import sys
from PIL import Image
import statistics

def analyze_histogram(image_path):
    """分析图片颜色直方图"""
    try:
        img = Image.open(image_path)

        # 转换为RGB
        if img.mode != 'RGB':
            img = img.convert('RGB')

        # 获取直方图
        histogram = img.histogram()

        # 分离RGB通道
        r_hist = histogram[0:256]
        g_hist = histogram[256:512]
        b_hist = histogram[512:768]

        # 计算统计信息
        def get_stats(channel, name):
            max_val = max(channel)
            min_val = min(channel)
            avg_val = statistics.mean(channel)
            max_idx = channel.index(max_val)

            return f"{name}通道: 峰值={max_val} (颜色值={max_idx}), 最小值={min_val}, 平均值={avg_val:.1f}"

        result = "颜色直方图分析:\n"
        result += get_stats(r_hist, "红色") + "\n"
        result += get_stats(g_hist, "绿色") + "\n"
        result += get_stats(b_hist, "蓝色") + "\n"

        # 计算整体亮度
        brightness = sum([i * r_hist[i] for i in range(256)]) / sum(r_hist)
        result += f"\n整体亮度: {brightness:.1f}"

        return result
    except Exception as e:
        return f"错误: {str(e)}"

if __name__ == "__main__":
    if len(sys.argv) > 1:
        result = analyze_histogram(sys.argv[1])
        print(result)
