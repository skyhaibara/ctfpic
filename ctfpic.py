import sys
import os
import subprocess
import json
from PIL import Image, ImageFile, ExifTags
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QFileDialog,
                             QTextEdit, QGroupBox, QMessageBox, QComboBox,
                             QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
                             QShortcut, QMenu, QAbstractItemView)
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QThread, QTimer
from PyQt5.QtGui import (QPixmap, QFont, QIcon, QPalette, QColor,
                         QTextCharFormat, QTextCursor, QBrush, QKeySequence)

# 确保可以加载各种格式的图片
ImageFile.LOAD_TRUNCATED_IMAGES = True


class ScriptExecutor(QThread):
    """脚本执行线程"""
    output_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(str)

    def __init__(self, script_path, image_path):
        super().__init__()
        self.script_path = script_path
        self.image_path = image_path

    def run(self):
        try:
            # 执行脚本
            result = subprocess.run(
                [sys.executable, self.script_path, self.image_path],
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=30
            )

            output_text = f"脚本: {os.path.basename(self.script_path)}\n"
            output_text += f"命令行: {sys.executable} {os.path.basename(self.script_path)} {os.path.basename(self.image_path)}\n\n"

            if result.stdout:
                output_text += f"输出:\n{result.stdout}\n"

            if result.stderr:
                output_text += f"错误:\n{result.stderr}\n"

            if result.returncode != 0:
                output_text += f"返回码: {result.returncode}"

            self.output_signal.emit(output_text)
            self.finished_signal.emit("脚本执行完成")

        except subprocess.TimeoutExpired:
            self.output_signal.emit("脚本执行超时（30秒）")
            self.finished_signal.emit("脚本执行超时")
        except Exception as e:
            self.output_signal.emit(f"执行脚本时出错: {str(e)}")
            self.finished_signal.emit("脚本执行失败")


class PhotoAnalyzerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_image_path = None
        self.script_files = []
        self.script_executor = None
        self.current_exif_data = {}  # 存储当前的EXIF数据
        self.init_ui()
        self.load_scripts()
        self.setup_clipboard_functionality()
        self.exif_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.exif_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.comment_preview = QTextEdit()
        self.comment_preview.setReadOnly(True)
        self.comment_preview.setPlaceholderText("EXIF 备注 / Flag 将在这里集中显示")

    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("CTF-PIC")
        self.setGeometry(100, 100, 1000, 800)

        if os.path.exists("icon.png"):
            self.setWindowIcon(QIcon("icon.png"))

        # 设置应用样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #4a86e8;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3a76d8;
            }
            QPushButton:disabled {
                background-color: #a0a0a0;
            }
            QLabel {
                color: #333333;
            }
            QTextEdit {
                background-color: white;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 5px;
                font-family: "Consolas", "Monaco", monospace;
            }
            QTableWidget {
                background-color: white;
                border: 1px solid #cccccc;
                border-radius: 4px;
                gridline-color: #e0e0e0;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 5px;
                border: 1px solid #e0e0e0;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        title_label = QLabel("📸 CTF-PIC")
        title_label.setFont(QFont("Arial", 20, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; margin: 10px; padding: 10px;")
        main_layout.addWidget(title_label)

        self.tab_widget = QTabWidget()
        self.create_analysis_tab()
        self.create_script_tab()
        main_layout.addWidget(self.tab_widget)

        self.status_bar = self.statusBar()
        self.status_bar.showMessage("就绪")

    def setup_clipboard_functionality(self):
        """设置剪贴板功能"""
        if hasattr(self, 'exif_table'):
            self.exif_table.setContextMenuPolicy(Qt.CustomContextMenu)
            self.exif_table.customContextMenuRequested.connect(self.show_exif_context_menu)
            copy_shortcut = QShortcut(QKeySequence.Copy, self.exif_table)
            copy_shortcut.activated.connect(self.copy_selected_exif)

    def show_exif_context_menu(self, position):
        """显示EXIF表格的右键上下文菜单"""
        try:
            menu = QMenu(self)
            copy_action = menu.addAction("📋 复制选中内容")
            copy_action.triggered.connect(self.copy_selected_exif)
            copy_row_action = menu.addAction("📋 复制整行")
            copy_row_action.triggered.connect(lambda: self.copy_exif_row(position))
            copy_all_action = menu.addAction("📋 复制所有EXIF信息")
            copy_all_action.triggered.connect(self.copy_all_exif)
            menu.addSeparator()
            save_action = menu.addAction("💾 保存EXIF信息")
            save_action.triggered.connect(self.save_exif_info)
            menu.exec_(self.exif_table.viewport().mapToGlobal(position))
        except Exception as e:
            print(f"显示上下文菜单时出错: {str(e)}")

    def copy_selected_exif(self):
        table = self.exif_table
        selection = table.selectionModel().selectedRows()

        # 兜底：如果没有 selectedRows，用 currentRow
        if not selection:
            row = table.currentRow()
            if row >= 0:
                selection = [table.model().index(row, 0)]

        if not selection:
            QMessageBox.information(self, "提示", "请先选择一行EXIF信息")
            return

        lines = []
        for index in selection:
            row = index.row()
            key = table.item(row, 0)
            val = table.item(row, 1)
            if key and val:
                lines.append(f"{key.text()}: {val.text()}")

        QApplication.clipboard().setText("\n".join(lines))
        self.show_copy_feedback(f"已复制 {len(lines)} 行EXIF信息")

    def copy_exif_row(self, position):
        """复制指定行的EXIF信息 - 修复版"""
        try:
            if not hasattr(self, 'exif_table'):
                return

            row = self.exif_table.rowAt(position.y())
            if row < 0 or row >= self.exif_table.rowCount():
                return

            # 直接从表格中获取该行的内容
            property_item = self.exif_table.item(row, 0)
            value_item = self.exif_table.item(row, 1)

            if property_item and value_item:
                property_text = property_item.text()
                value_text = value_item.text()
                text_to_copy = f"{property_text}: {value_text}"

                clipboard = QApplication.clipboard()
                clipboard.setText(text_to_copy)

                self.show_copy_feedback(f"已复制行 {row + 1} 的EXIF信息")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"复制行时出错: {str(e)}")

    def copy_all_exif(self):
        """复制所有EXIF信息到剪贴板 - 修复版"""
        try:
            if not hasattr(self, 'exif_table') or not hasattr(self, 'current_image_path'):
                QMessageBox.information(self, "提示", "没有可复制的EXIF信息")
                return

            row_count = self.exif_table.rowCount()
            if row_count <= 0:
                QMessageBox.information(self, "提示", "没有可复制的EXIF信息")
                return

            # 从表格中直接获取所有行的内容
            exif_text = f"EXIF信息 - {os.path.basename(self.current_image_path)}\n"
            exif_text += "=" * 50 + "\n"

            for row in range(row_count):
                property_item = self.exif_table.item(row, 0)
                value_item = self.exif_table.item(row, 1)

                if property_item and value_item:
                    property_text = property_item.text()
                    value_text = value_item.text()
                    exif_text += f"{property_text}: {value_text}\n"

            # 复制到剪贴板
            clipboard = QApplication.clipboard()
            clipboard.setText(exif_text.strip())

            self.show_copy_feedback(f"已复制 {row_count} 条EXIF信息到剪贴板")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"复制所有EXIF信息时出错: {str(e)}")

    def show_copy_feedback(self, message):
        """显示复制成功的反馈"""
        try:
            self.status_bar.showMessage(message, 3000)

            original_style = """
                QPushButton {
                    background-color: #4a86e8;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #3a76d8;
                }
                QPushButton:disabled {
                    background-color: #a0a0a0;
                }
            """

            feedback_style = """
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-weight: bold;
                }
            """

            if hasattr(self, 'copy_selected_button') and self.copy_selected_button.isEnabled():
                self.copy_selected_button.setStyleSheet(feedback_style)
                QTimer.singleShot(500, lambda: self.copy_selected_button.setStyleSheet(original_style))

            if hasattr(self, 'copy_all_button') and self.copy_all_button.isEnabled():
                self.copy_all_button.setStyleSheet(feedback_style)
                QTimer.singleShot(500, lambda: self.copy_all_button.setStyleSheet(original_style))
        except Exception as e:
            print(f"显示复制反馈时出错: {str(e)}")

    def create_analysis_tab(self):
        """创建照片分析选项卡"""
        analysis_tab = QWidget()
        layout = QVBoxLayout(analysis_tab)

        # 上传按钮区域
        upload_group = QGroupBox("上传照片")
        upload_layout = QVBoxLayout()
        self.upload_button = QPushButton("📁 选择照片")
        self.upload_button.clicked.connect(self.upload_image)
        self.upload_button.setFixedHeight(40)
        upload_layout.addWidget(self.upload_button)

        self.image_info_label = QLabel("未选择照片")
        self.image_info_label.setAlignment(Qt.AlignCenter)
        self.image_info_label.setWordWrap(True)
        self.image_info_label.setStyleSheet("""
            QLabel {
                color: #666666;
                font-style: italic;
                padding: 10px;
                border: 2px dashed #cccccc;
                border-radius: 5px;
                background-color: #f9f9f9;
            }
        """)
        upload_layout.addWidget(self.image_info_label)
        upload_group.setLayout(upload_layout)
        layout.addWidget(upload_group)

        # 照片预览和分析结果区域
        analysis_group = QGroupBox("照片信息")
        analysis_layout = QHBoxLayout()

        # 左侧：照片预览
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)
        preview_title = QLabel("📷 照片预览")
        preview_title.setFont(QFont("Arial", 12, QFont.Bold))
        preview_title.setAlignment(Qt.AlignCenter)
        preview_layout.addWidget(preview_title)

        self.image_preview_label = QLabel("点击上方按钮选择照片")
        self.image_preview_label.setAlignment(Qt.AlignCenter)
        self.image_preview_label.setMinimumHeight(300)
        self.image_preview_label.setStyleSheet("""
            QLabel {
                background-color: #f8f8f8;
                border: 2px dashed #cccccc;
                border-radius: 8px;
                color: #888888;
                font-style: italic;
                padding: 20px;
            }
        """)
        preview_layout.addWidget(self.image_preview_label)

        basic_info_title = QLabel("📄 基本信息")
        basic_info_title.setFont(QFont("Arial", 10, QFont.Bold))
        preview_layout.addWidget(basic_info_title)

        self.basic_info_text = QTextEdit()
        self.basic_info_text.setReadOnly(True)
        self.basic_info_text.setMaximumHeight(150)
        preview_layout.addWidget(self.basic_info_text)
        analysis_layout.addWidget(preview_widget, 1)

        # 右侧：EXIF信息
        exif_widget = QWidget()
        exif_layout = QVBoxLayout(exif_widget)
        exif_title = QLabel("🔍 EXIF信息")
        exif_title.setFont(QFont("Arial", 12, QFont.Bold))
        exif_title.setAlignment(Qt.AlignCenter)
        exif_layout.addWidget(exif_title)

        # EXIF表格
        self.exif_table = QTableWidget()
        self.exif_table.setColumnCount(2)
        self.exif_table.setHorizontalHeaderLabels(["属性", "值"])
        self.exif_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.exif_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.exif_table.verticalHeader().setVisible(False)
        self.exif_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.exif_table.setSelectionMode(QTableWidget.ExtendedSelection)
        exif_layout.addWidget(self.exif_table)

        # 添加复制按钮区域
        exif_button_layout = QHBoxLayout()
        self.save_exif_button = QPushButton("💾 保存为文件")
        self.save_exif_button.clicked.connect(self.save_exif_info)
        self.save_exif_button.setEnabled(False)
        exif_button_layout.addWidget(self.save_exif_button)

        exif_button_layout.addStretch(1)
        exif_layout.addLayout(exif_button_layout)
        analysis_layout.addWidget(exif_widget, 1)
        analysis_group.setLayout(analysis_layout)
        layout.addWidget(analysis_group)
        self.tab_widget.addTab(analysis_tab, "照片分析")

    def create_script_tab(self):
        """创建脚本执行选项卡"""
        script_tab = QWidget()
        layout = QVBoxLayout(script_tab)
        script_group = QGroupBox("脚本执行")
        script_layout = QVBoxLayout()
        script_instruction = QLabel("从scripts文件夹中选择并执行Python脚本：")
        script_layout.addWidget(script_instruction)

        script_select_layout = QHBoxLayout()
        script_select_layout.addWidget(QLabel("选择脚本:"))
        self.script_combo = QComboBox()
        self.script_combo.addItem("请选择脚本")
        self.script_combo.currentIndexChanged.connect(self.on_script_selected)
        script_select_layout.addWidget(self.script_combo)
        script_layout.addLayout(script_select_layout)

        self.script_info_label = QLabel("脚本信息将在这里显示")
        self.script_info_label.setWordWrap(True)
        self.script_info_label.setStyleSheet("""
            QLabel {
                padding: 10px;
                border: 1px solid #e0e0e0;
                border-radius: 5px;
                background-color: #f9f9f9;
            }
        """)
        script_layout.addWidget(self.script_info_label)

        self.execute_button = QPushButton("▶ 执行脚本")
        self.execute_button.clicked.connect(self.execute_script)
        self.execute_button.setEnabled(False)
        script_layout.addWidget(self.execute_button)

        script_output_label = QLabel("脚本输出:")
        script_output_label.setFont(QFont("Arial", 10, QFont.Bold))
        script_layout.addWidget(script_output_label)

        self.script_output_text = QTextEdit()
        self.script_output_text.setReadOnly(True)
        self.script_output_text.setPlaceholderText("脚本输出将显示在这里...")
        script_layout.addWidget(self.script_output_text)
        script_group.setLayout(script_layout)
        layout.addWidget(script_group)
        self.tab_widget.addTab(script_tab, "脚本执行")

    def load_scripts(self):
        """加载scripts文件夹中的Python脚本"""
        scripts_dir = "scripts"
        if not os.path.exists(scripts_dir):
            os.makedirs(scripts_dir, exist_ok=True)
            self.status_bar.showMessage("scripts文件夹已创建，请添加Python脚本")
        else:
            self.script_files = []
            for file in os.listdir(scripts_dir):
                if file.endswith(".py"):
                    self.script_files.append(file)

            self.script_combo.clear()
            self.script_combo.addItem("请选择脚本")
            for script in self.script_files:
                self.script_combo.addItem(script)

            if self.script_files:
                self.status_bar.showMessage(f"在scripts文件夹中找到 {len(self.script_files)} 个脚本")
            else:
                self.status_bar.showMessage("scripts文件夹中没有找到Python脚本")

    def on_script_selected(self, index):
        """脚本被选中时的处理"""
        if index > 0:
            script_name = self.script_combo.currentText()
            script_path = os.path.join("scripts", script_name)

            if os.path.exists(script_path):
                try:
                    with open(script_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()

                    script_info = f"脚本: {script_name}\n"
                    comment_lines = []
                    for i, line in enumerate(lines[:5]):
                        stripped = line.strip()
                        if stripped.startswith('#'):
                            comment = stripped[1:].strip()
                            if comment:
                                comment_lines.append(comment)
                        elif stripped:
                            break

                    if comment_lines:
                        script_info += f"描述: {comment_lines[0]}\n"
                        if len(comment_lines) > 1:
                            script_info += f"功能: {comment_lines[1]}"

                    self.script_info_label.setText(script_info)

                except Exception as e:
                    self.script_info_label.setText(f"脚本: {script_name}\n无法读取脚本信息: {str(e)}")
            else:
                self.script_info_label.setText(f"脚本文件不存在: {script_name}")
        else:
            self.script_info_label.setText("脚本信息将在这里显示")

    def upload_image(self):
        """上传图片并分析"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择照片",
            "",
            "图片文件 (*.jpg *.jpeg *.png *.bmp *.gif *.tiff *.webp);;所有文件 (*.*)"
        )

        if file_path:
            self.current_image_path = file_path
            self.analyze_image(file_path)

    def analyze_image(self, image_path):
        """分析图片的宽高、文件类型和EXIF信息"""
        try:
            with Image.open(image_path) as img:
                width, height = img.size
                mode = img.mode
                format_name = img.format if img.format else "未知"
                file_size = os.path.getsize(image_path) / 1024
                file_ext = os.path.splitext(image_path)[1].lower()
                stat_info = os.stat(image_path)
                create_time = datetime.fromtimestamp(stat_info.st_ctime).strftime('%Y-%m-%d %H:%M:%S')
                modify_time = datetime.fromtimestamp(stat_info.st_mtime).strftime('%Y-%m-%d %H:%M:%S')

                file_name = os.path.basename(image_path)
                self.image_info_label.setText(f"✅ 已选择: {file_name}\n📁 路径: {image_path}")
                self.image_info_label.setStyleSheet("""
                    QLabel {
                        color: #27ae60;
                        font-weight: bold;
                        padding: 10px;
                        border: 2px solid #27ae60;
                        border-radius: 5px;
                        background-color: #f0f9f0;
                    }
                """)

                # 显示预览
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(
                        QSize(400, 300),
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation
                    )
                    self.image_preview_label.setPixmap(scaled_pixmap)
                    self.image_preview_label.setText("")
                else:
                    self.image_preview_label.setText("无法加载图片预览")

                # 显示基本信息
                basic_info = f"""📄 文件信息:
• 文件名: {file_name}
• 文件类型: {format_name} ({file_ext})
• 文件大小: {file_size:.2f} KB
• 图片尺寸: {width} × {height} 像素
• 颜色模式: {mode}
• 创建时间: {create_time}
• 修改时间: {modify_time}"""

                self.basic_info_text.setText(basic_info)
                self.display_exif_info(img)
                self.execute_button.setEnabled(True)
                self.save_exif_button.setEnabled(True)
                self.status_bar.showMessage(f"已加载图片: {file_name}")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法分析图片: {str(e)}")
            self.status_bar.showMessage("图片分析失败")

    def display_exif_info(self, img):
        exif_data = img._getexif()
        self.exif_table.clearContents()
        self.current_exif_data.clear()

        if not exif_data:
            self.exif_table.setRowCount(1)
            self.exif_table.setItem(0, 0, QTableWidgetItem("无EXIF信息"))
            self.exif_table.setItem(0, 1, QTableWidgetItem(""))
            return

        exif_items = []

        for tag_id, value in exif_data.items():
            tag_name = ExifTags.TAGS.get(tag_id)
            if not tag_name:
                continue
            if tag_name in ("Padding", "MakerNote"):
                continue

            if isinstance(value, bytes):
                # XPComment / XPTitle / XPKeywords 等（UTF-16LE）
                if tag_id in (40091, 40092, 40093, 40094, 40095, 59932):
                    try:
                        value = value.decode('utf-16le', errors='ignore').rstrip('\x00')
                    except Exception:
                        value = repr(value)
                # UserComment（通常以 ASCII\0\0\0 开头）
                elif value.startswith(b'ASCII'):
                    try:
                        value = value[8:].decode('ascii', errors='ignore')
                    except Exception:
                        value = repr(value)
                else:
                    # 保留原始 bytes
                    value = repr(value)

            exif_items.append((tag_name, str(value)))

        if not exif_items:
            self.exif_table.setRowCount(1)
            self.exif_table.setItem(0, 0, QTableWidgetItem("无可显示EXIF信息"))
            self.exif_table.setItem(0, 1, QTableWidgetItem(""))
            return

        self.exif_table.setRowCount(len(exif_items))
        for row, (k, v) in enumerate(sorted(exif_items)):
            self.exif_table.setItem(row, 0, QTableWidgetItem(k))
            self.exif_table.setItem(row, 1, QTableWidgetItem(v))

    def save_exif_info(self):
        """保存EXIF信息到文件"""
        if not self.current_image_path:
            QMessageBox.warning(self, "警告", "请先选择一张图片")
            return

        file_name = os.path.splitext(os.path.basename(self.current_image_path))[0]
        default_path = f"{file_name}_exif.json"

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存EXIF信息",
            default_path,
            "JSON文件 (*.json);;文本文件 (*.txt);;所有文件 (*.*)"
        )

        if save_path:
            try:
                with Image.open(self.current_image_path) as img:
                    exif_data = img._getexif()

                    if exif_data is not None:
                        serializable_exif = {}
                        for tag_id, value in exif_data.items():
                            tag_name = ExifTags.TAGS.get(tag_id, tag_id)
                            if isinstance(value, bytes):
                                try:
                                    value = value.decode('utf-8', errors='ignore')
                                except:
                                    value = str(value)
                            elif isinstance(value, tuple) or isinstance(value, list):
                                value = str(value)
                            serializable_exif[str(tag_name)] = str(value)

                        if save_path.endswith('.json'):
                            with open(save_path, 'w', encoding='utf-8') as f:
                                json.dump(serializable_exif, f, indent=2, ensure_ascii=False)
                        else:
                            with open(save_path, 'w', encoding='utf-8') as f:
                                f.write("EXIF信息:\n")
                                f.write("=" * 50 + "\n")
                                for tag, value in serializable_exif.items():
                                    f.write(f"{tag}: {value}\n")

                        QMessageBox.information(self, "成功", f"EXIF信息已保存到:\n{save_path}")
                        self.status_bar.showMessage(f"EXIF信息已保存: {os.path.basename(save_path)}")
                    else:
                        QMessageBox.warning(self, "警告", "图片中没有EXIF信息")

            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存EXIF信息时出错: {str(e)}")

    def execute_script(self):
        """执行scripts文件夹中的Python脚本"""
        if not self.current_image_path:
            QMessageBox.warning(self, "警告", "请先选择一张图片")
            return

        selected_script = self.script_combo.currentText()
        if selected_script == "请选择脚本":
            QMessageBox.warning(self, "警告", "请选择一个脚本")
            return

        script_path = os.path.join("scripts", selected_script)
        if not os.path.exists(script_path):
            QMessageBox.critical(self, "错误", f"脚本不存在: {script_path}")
            return

        self.script_output_text.clear()
        self.execute_button.setEnabled(False)
        self.execute_button.setText("执行中...")

        self.script_executor = ScriptExecutor(script_path, self.current_image_path)
        self.script_executor.output_signal.connect(self.on_script_output)
        self.script_executor.finished_signal.connect(self.on_script_finished)
        self.script_executor.start()

        self.status_bar.showMessage(f"正在执行脚本: {selected_script}...")

    def on_script_output(self, output):
        """处理脚本输出"""
        self.script_output_text.append(output)

    def on_script_finished(self, message):
        """脚本执行完成"""
        self.execute_button.setEnabled(True)
        self.execute_button.setText("▶ 执行脚本")
        self.status_bar.showMessage(message)
        cursor = self.script_output_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.script_output_text.setTextCursor(cursor)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    app_icon = QIcon.fromTheme("camera-photo")
    if app_icon.isNull():
        app_icon = app.style().standardIcon(app.style().SP_DesktopIcon)
    app.setWindowIcon(app_icon)

    window = PhotoAnalyzerApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()