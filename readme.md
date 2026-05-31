# CTF-PIC 图片隐写分析辅助工具

## 一、项目简介

CTF-PIC 是一个面向 CTF（Capture The Flag）竞赛中**图片隐写分析场景**的辅助工具。
该工具通过图形化界面整合了图片基本信息查看、EXIF 元数据解析以及脚本化分析能力，旨在降低图片隐写题目的分析成本，提高参赛者在比赛或日常练习中的分析效率。

本项目主要用于对可疑图片进行初步分析，并为后续的隐写取证或脚本分析提供基础支持。

---

## 二、主要功能

- **图片基本信息**：文件名、格式、大小、尺寸、颜色模式、创建/修改时间，并实时预览。
- **EXIF 元数据解析**：表格化展示 EXIF 标签；自动解码 `UserComment`、`XPComment` 等常带备注/flag 的字段（UTF-16LE / ASCII）。
- **备注 / Flag 集中显示**：自动从 EXIF 备注字段与脚本输出中提取形如 `flag{...}`、`ctf{...}`、`picoCTF{...}` 的内容并高亮汇总，避免遗漏。
- **EXIF 复制 / 导出**：右键菜单或按钮复制选中行 / 全部，支持导出为 JSON / TXT。
- **AI 生图识别**：基于元数据 / 签名检测 Stable Diffusion、ComfyUI、NovelAI、DALL·E、Midjourney、Adobe Firefly 及 C2PA 内容凭证等特征（见 `scripts/ai_detect.py`）。
- **脚本化分析**：在 `scripts/` 目录放入独立 Python 脚本，界面中选择并对当前图片一键执行，输出实时回显（脚本输出中的 flag 也会被自动捕获）。脚本生成的文件统一归类到 `output/<脚本名>/` 目录下。
- **深色界面**：现代深色主题，长时间看图 / 做题更护眼。

---

## 三、运行环境说明（环境配置说明）

本项目基于 **Python 3.12** 开发与测试，请确保运行环境满足以下要求。

```shell
pip install -r requirements.txt

python ctfpic.py
```

> 提示：图标与 `scripts/` 目录均以 `ctfpic.py` 所在目录为基准定位，可在任意工作目录下启动。

---

## 四、内置分析脚本（scripts/）

| 脚本 | 说明 |
| --- | --- |
| `base_analyze.py` | 基础分析：尺寸/模式/格式、前 100 像素 LSB、文件尾字节预览 |
| `lsb.py` | LSB（最低有效位）隐写分析：分通道统计、ASCII/HEX 解码、文件头与隐写工具特征检测、尝试提取 |
| `analyze_histogram.py` | RGB 颜色直方图统计与整体亮度 |
| `gif.py` | APNG 帧延时分析，尝试从延时序列还原隐藏信息 |
| `enhance_contrast.py` | 颜色块对比度增强，凸显纯色块中隐藏的信息 |
| `file_append.py` | 文件尾附加数据检测 + 全文件嵌入文件签名扫描（binwalk 简化版），自动保存附加数据 |
| `png_chunks.py` | 解析 PNG 全部区块、校验 CRC，并解码 tEXt/zTXt/iTXt 文本块 |
| `bit_plane.py` | 导出各 RGB 通道指定位平面为黑白图，可视化 LSB 隐写 |
| `ai_detect.py` | 基于元数据 / 签名识别 AI 生成图片（SD/ComfyUI/NovelAI/DALL·E/Midjourney/Firefly/C2PA） |

> **AI 识别说明**：本功能基于**元数据 / 内容凭证**判断，命中即较可靠；但元数据可被截图、转存或工具清除，**未命中不代表一定是真实拍摄**，不做像素级模型推断。

### 命令行单独使用

所有脚本均可脱离界面直接运行：

```shell
python scripts/lsb.py <图片路径>
python scripts/lsb.py <图片路径> --extract     # 尝试提取 LSB 隐藏文件
python scripts/lsb.py <图片路径> --search      # 搜索 flag / URL / base64

python scripts/file_append.py <图片路径>
python scripts/png_chunks.py <图片路径>
python scripts/bit_plane.py <图片路径> 0,1,2   # 可选：指定导出的位平面，默认仅 LSB(bit0)
python scripts/ai_detect.py <图片路径>
```

> 在界面中执行时，脚本生成的文件（提取出的数据、位平面图等）会统一保存到 `output/<脚本名>/` 目录下；直接命令行运行时则保存在当前工作目录。

---

## 五、扩展自己的脚本

向 `scripts/` 目录添加任意接收图片路径作为第一个命令行参数的 Python 脚本即可在界面中调用。约定：

- 通过 `sys.argv[1]` 读取图片路径，分析结果用 `print` 输出（界面会捕获 stdout）。
- 文件**前两行注释**会作为界面中的「描述 / 功能」展示，例如：

  ```python
  # 我的分析脚本
  # 检测图片中的某种隐写特征
  ```

- 若输出包含 emoji 等非 ASCII 字符，建议在脚本开头加入以下两行，避免中文 Windows 下编码报错：

  ```python
  import sys
  if hasattr(sys.stdout, "reconfigure"):
      sys.stdout.reconfigure(encoding="utf-8")
  ```
