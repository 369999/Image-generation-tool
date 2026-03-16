import os
import sys
from typing import List, Optional

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QImage, QPixmap, QColor
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from PIL import Image, ImageDraw, ImageQt


class ImageGeneratorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("图片生成工具 V0.1")
        self.resize(1200, 800)

        self.preview_image = None       # 当前预览图对象
        self.batch_preview_items = []   # 批量预览条目缓存

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        left_panel = self._build_left_panel()
        right_panel = self._build_right_panel()

        # 左侧控制面板固定宽度，右侧预览区自适应
        main_layout.addWidget(left_panel, 0)
        main_layout.addWidget(right_panel, 1)

        self.update_preview()

    # ──────────────────────────────────────────────
    # UI 构建
    # ──────────────────────────────────────────────

    def _build_left_panel(self) -> QWidget:
        """构建左侧参数控制面板，包含所有设置组和操作按钮。"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(12)

        # ── 基础设置 ──────────────────────────────
        basic_group = QGroupBox("基础设置")
        basic_form = QFormLayout(basic_group)

        # 输出图片格式选择
        self.format_combo = QComboBox()
        self.format_combo.addItems(["PNG", "JPEG", "BMP"])
        self.format_combo.currentTextChanged.connect(self.update_preview)
        basic_form.addRow("图片格式：", self.format_combo)

        # 输出轮廓形状：矩形 / 圆形裁切
        self.shape_combo = QComboBox()
        self.shape_combo.addItems(["矩形图", "圆形图"])
        self.shape_combo.currentTextChanged.connect(self.update_preview)
        basic_form.addRow("输出形状：", self.shape_combo)

        # 图片宽度（像素）
        self.width_spin = QSpinBox()
        self.width_spin.setRange(16, 8192)
        self.width_spin.setValue(512)
        self.width_spin.valueChanged.connect(self.update_preview)
        basic_form.addRow("宽度：", self.width_spin)

        # 图片高度（像素）
        self.height_spin = QSpinBox()
        self.height_spin.setRange(16, 8192)
        self.height_spin.setValue(512)
        self.height_spin.valueChanged.connect(self.update_preview)
        basic_form.addRow("高度：", self.height_spin)

        # 生成类型：决定显示哪个专属设置组
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "WRGB不同灰阶图片",
            "黑底白圆图（10%-100%）",
            "棋盘格图片",
            "寿命图片",
        ])
        self.type_combo.currentTextChanged.connect(self.on_type_changed)
        basic_form.addRow("生成类型：", self.type_combo)

        layout.addWidget(basic_group)

        # ── 灰阶图设置 ────────────────────────────
        gray_group = QGroupBox("灰阶图设置")
        gray_form = QFormLayout(gray_group)

        # 选择 WRGB 中的一个通道
        self.gray_channel_combo = QComboBox()
        self.gray_channel_combo.addItems(["W（白）", "R（红）", "G（绿）", "B（蓝）"])
        self.gray_channel_combo.currentTextChanged.connect(self.update_preview)
        gray_form.addRow("颜色通道：", self.gray_channel_combo)

        # 当前预览/单张导出时使用的灰阶值
        self.gray_value_spin = QSpinBox()
        self.gray_value_spin.setRange(0, 255)
        self.gray_value_spin.setValue(128)
        self.gray_value_spin.valueChanged.connect(self.update_preview)
        gray_form.addRow("灰阶值（0-255）：", self.gray_value_spin)

        gray_form.addRow(QLabel("── 批量导出设置 ──"))

        # 是否同时导出 WRGB 全部四个通道
        self.gray_all_channels_check = QCheckBox("导出全部通道（WRGB）")
        gray_form.addRow(self.gray_all_channels_check)

        # 批量起始灰阶值
        self.gray_batch_start_spin = QSpinBox()
        self.gray_batch_start_spin.setRange(0, 255)
        self.gray_batch_start_spin.setValue(0)
        gray_form.addRow("批量起始值：", self.gray_batch_start_spin)

        # 批量结束灰阶值
        self.gray_batch_end_spin = QSpinBox()
        self.gray_batch_end_spin.setRange(0, 255)
        self.gray_batch_end_spin.setValue(255)
        gray_form.addRow("批量结束值：", self.gray_batch_end_spin)

        # 批量步长
        self.gray_batch_step_spin = QSpinBox()
        self.gray_batch_step_spin.setRange(1, 255)
        self.gray_batch_step_spin.setValue(1)
        gray_form.addRow("步长：", self.gray_batch_step_spin)

        layout.addWidget(gray_group)
        self.gray_group = gray_group

        # ── 棋盘格设置 ────────────────────────────
        checker_group = QGroupBox("棋盘格设置")
        checker_form = QFormLayout(checker_group)

        # 黑格宽度（像素）
        self.checker_black_w_spin = QSpinBox()
        self.checker_black_w_spin.setRange(1, 2048)
        self.checker_black_w_spin.setValue(40)
        self.checker_black_w_spin.valueChanged.connect(self.update_preview)
        checker_form.addRow("黑格宽度：", self.checker_black_w_spin)

        # 黑格高度（像素）
        self.checker_black_h_spin = QSpinBox()
        self.checker_black_h_spin.setRange(1, 2048)
        self.checker_black_h_spin.setValue(40)
        self.checker_black_h_spin.valueChanged.connect(self.update_preview)
        checker_form.addRow("黑格高度：", self.checker_black_h_spin)

        # 白格宽度（像素）
        self.checker_white_w_spin = QSpinBox()
        self.checker_white_w_spin.setRange(1, 2048)
        self.checker_white_w_spin.setValue(40)
        self.checker_white_w_spin.valueChanged.connect(self.update_preview)
        checker_form.addRow("白格宽度：", self.checker_white_w_spin)

        # 白格高度（像素）
        self.checker_white_h_spin = QSpinBox()
        self.checker_white_h_spin.setRange(1, 2048)
        self.checker_white_h_spin.setValue(40)
        self.checker_white_h_spin.valueChanged.connect(self.update_preview)
        checker_form.addRow("白格高度：", self.checker_white_h_spin)

        layout.addWidget(checker_group)
        self.checker_group = checker_group

        # ── 寿命图片设置 ──────────────────────────
        lifetime_group = QGroupBox("寿命图片设置")
        lifetime_form = QFormLayout(lifetime_group)

        # 中心黑色圆形的半径（像素）
        self.lifetime_radius_spin = QSpinBox()
        self.lifetime_radius_spin.setRange(1, 4096)
        self.lifetime_radius_spin.setValue(100)
        self.lifetime_radius_spin.valueChanged.connect(self.update_preview)
        lifetime_form.addRow("圆形半径（px）：", self.lifetime_radius_spin)

        layout.addWidget(lifetime_group)
        self.lifetime_group = lifetime_group

        # ── 批量生成设置（黑底白圆图专用）────────
        batch_group = QGroupBox("批量生成")
        batch_layout = QVBoxLayout(batch_group)

        # 勾选后启用黑底白圆图批量模式
        self.batch_enable = QCheckBox("启用批量生成")
        self.batch_enable.stateChanged.connect(self.update_preview)
        batch_layout.addWidget(self.batch_enable)

        batch_grid = QGridLayout()

        # 批量起始百分比（10%~100%，步长 10）
        self.batch_start_spin = QSpinBox()
        self.batch_start_spin.setRange(10, 100)
        self.batch_start_spin.setSingleStep(10)
        self.batch_start_spin.setValue(10)
        batch_grid.addWidget(QLabel("起始百分比："), 0, 0)
        batch_grid.addWidget(self.batch_start_spin, 0, 1)

        # 批量结束百分比
        self.batch_end_spin = QSpinBox()
        self.batch_end_spin.setRange(10, 100)
        self.batch_end_spin.setSingleStep(10)
        self.batch_end_spin.setValue(100)
        batch_grid.addWidget(QLabel("结束百分比："), 1, 0)
        batch_grid.addWidget(self.batch_end_spin, 1, 1)

        # 批量步长
        self.batch_step_spin = QSpinBox()
        self.batch_step_spin.setRange(10, 100)
        self.batch_step_spin.setSingleStep(10)
        self.batch_step_spin.setValue(10)
        batch_grid.addWidget(QLabel("步长："), 2, 0)
        batch_grid.addWidget(self.batch_step_spin, 2, 1)

        for widget in [self.batch_start_spin, self.batch_end_spin, self.batch_step_spin]:
            widget.valueChanged.connect(self.update_preview)

        batch_layout.addLayout(batch_grid)

        # 批量列表预览（显示将生成的百分比序列）
        self.batch_list = QListWidget()
        batch_layout.addWidget(self.batch_list)

        layout.addWidget(batch_group)
        self.batch_group = batch_group

        # ── 操作按钮区 ────────────────────────────
        btn_layout = QHBoxLayout()

        self.preview_btn = QPushButton("刷新预览")
        self.preview_btn.clicked.connect(self.update_preview)
        btn_layout.addWidget(self.preview_btn)

        self.save_single_btn = QPushButton("保存当前图片")
        self.save_single_btn.clicked.connect(self.save_single_image)
        btn_layout.addWidget(self.save_single_btn)

        # 批量导出黑底白圆图
        self.save_batch_btn = QPushButton("批量导出")
        self.save_batch_btn.clicked.connect(self.save_batch_images)
        btn_layout.addWidget(self.save_batch_btn)

        # 批量导出 WRGB 灰阶图
        self.save_batch_gray_btn = QPushButton("批量导出灰阶图")
        self.save_batch_gray_btn.clicked.connect(self.save_batch_gray_images)
        btn_layout.addWidget(self.save_batch_gray_btn)

        layout.addLayout(btn_layout)

        layout.addStretch(1)

        # 初始化各设置组的可见性（不触发预览，由 __init__ 统一调用）
        self._update_group_visibility(self.type_combo.currentText())
        return panel

    def _build_right_panel(self) -> QWidget:
        """构建右侧实时预览面板。"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        title = QLabel("实时预览")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(QSize(640, 640))
        self.preview_label.setStyleSheet(
            "border: 1px solid #999; background-color: #f5f5f5;"
        )

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.preview_label)
        layout.addWidget(scroll)

        return panel

    # ──────────────────────────────────────────────
    # 事件处理
    # ──────────────────────────────────────────────

    def on_type_changed(self):
        """生成类型切换时，更新各设置组可见性并刷新预览。"""
        current = self.type_combo.currentText()
        self._update_group_visibility(current)
        self.update_preview()

    def _update_group_visibility(self, current_type: str):
        """根据当前生成类型，显示/隐藏对应的专属设置组。"""
        self.gray_group.setVisible(current_type == "WRGB不同灰阶图片")
        self.checker_group.setVisible(current_type == "棋盘格图片")
        self.lifetime_group.setVisible(current_type == "寿命图片")
        # 批量生成设置仅供"黑底白圆图"使用
        self.batch_group.setVisible(current_type == "黑底白圆图（10%-100%）")

    # ──────────────────────────────────────────────
    # 数据辅助
    # ──────────────────────────────────────────────

    def get_batch_percentages(self) -> List[int]:
        """返回黑底白圆图批量导出的百分比列表（10 的倍数，范围 10~100）。"""
        start = self.batch_start_spin.value()
        end = self.batch_end_spin.value()
        step = self.batch_step_spin.value()

        if step <= 0:
            return [10]
        if start > end:
            start, end = end, start

        values = list(range(start, end + 1, step))
        valid_values = [v for v in values if 10 <= v <= 100 and v % 10 == 0]
        return valid_values or [10]

    # ──────────────────────────────────────────────
    # 图片生成核心逻辑
    # ──────────────────────────────────────────────

    def generate_image(self, percentage: Optional[int] = None) -> Image.Image:
        """
        根据当前 UI 参数生成一张图片。
        percentage：仅供黑底白圆图批量模式使用，指定圆的覆盖百分比。
        """
        width = self.width_spin.value()
        height = self.height_spin.value()
        img_type = self.type_combo.currentText()
        shape = self.shape_combo.currentText()

        if img_type == "WRGB不同灰阶图片":
            # 取通道首字母 W/R/G/B
            channel = self.gray_channel_combo.currentText()[0]
            value = self.gray_value_spin.value()
            image = self.generate_wrgb_gray(width, height, channel, value)

        elif img_type == "黑底白圆图（10%-100%）":
            image = self.generate_black_white_circle(width, height, percentage)

        elif img_type == "棋盘格图片":
            bw = self.checker_black_w_spin.value()
            bh = self.checker_black_h_spin.value()
            ww = self.checker_white_w_spin.value()
            wh = self.checker_white_h_spin.value()
            image = self.generate_checkerboard(width, height, bw, bh, ww, wh)

        elif img_type == "寿命图片":
            radius = self.lifetime_radius_spin.value()
            image = self.generate_lifetime_image(width, height, radius)

        else:
            image = Image.new("RGBA", (width, height), (0, 0, 0, 255))

        # 如果选择圆形输出，对图片应用椭圆遮罩
        if shape == "圆形图":
            image = self.apply_circle_mask(image)

        return image

    def generate_wrgb_gray(self, width: int, height: int, channel: str, value: int) -> Image.Image:
        """
        生成单色纯填充灰阶图。
        channel: 'W'=灰白(R=G=B=value), 'R'=红, 'G'=绿, 'B'=蓝
        value:   0~255 亮度值
        """
        channel_colors = {
            "W": (value, value, value, 255),
            "R": (value, 0,     0,     255),
            "G": (0,     value, 0,     255),
            "B": (0,     0,     value, 255),
        }
        color = channel_colors.get(channel, (value, value, value, 255))
        return Image.new("RGBA", (width, height), color)

    def generate_black_white_circle(self, width: int, height: int, percentage: Optional[int]) -> Image.Image:
        """
        生成黑底白圆图。
        percentage=None 时绘制 10%~100% 的同心圆轮廓；
        percentage=N 时绘制覆盖 N% 面积的实心白圆。
        """
        image = Image.new("RGBA", (width, height), (0, 0, 0, 255))
        draw = ImageDraw.Draw(image)
        center_x, center_y = width // 2, height // 2

        if percentage is None:
            # 预览模式：显示所有百分比的同心圆轮廓
            for p in range(10, 101, 10):
                radius = int(min(width, height) * p / 200)
                bbox = [center_x - radius, center_y - radius,
                        center_x + radius, center_y + radius]
                draw.ellipse(bbox, outline=(255, 255, 255, 255), width=2)
        else:
            # 单张模式：填充指定百分比大小的实心圆
            radius = int(min(width, height) * percentage / 200)
            bbox = [center_x - radius, center_y - radius,
                    center_x + radius, center_y + radius]
            draw.ellipse(bbox, fill=(255, 255, 255, 255))

        return image

    def generate_checkerboard(
        self,
        width: int, height: int,
        black_w: int, black_h: int,
        white_w: int, white_h: int,
    ) -> Image.Image:
        """
        生成自定义黑白格尺寸的棋盘格图片。
        黑格和白格可以有各自独立的宽度与高度。
        左上角起始格为黑色，按 (行+列) 的奇偶性交替着色。
        """
        # 白色背景（白格直接由背景呈现，只需绘制黑格）
        image = Image.new("RGBA", (width, height), (255, 255, 255, 255))
        draw = ImageDraw.Draw(image)

        # 计算每一列的 x 坐标范围和列索引（奇偶决定宽度）
        cols = []
        x = 0
        col_idx = 0
        while x < width:
            cw = black_w if col_idx % 2 == 0 else white_w
            cols.append((x, min(x + cw, width), col_idx))
            x += cw
            col_idx += 1

        # 计算每一行的 y 坐标范围和行索引（奇偶决定高度）
        rows = []
        y = 0
        row_idx = 0
        while y < height:
            rh = black_h if row_idx % 2 == 0 else white_h
            rows.append((y, min(y + rh, height), row_idx))
            y += rh
            row_idx += 1

        # (行索引 + 列索引) 为偶数时填充黑色
        for (y0, y1, ri) in rows:
            for (x0, x1, ci) in cols:
                if (ri + ci) % 2 == 0:
                    draw.rectangle([x0, y0, x1 - 1, y1 - 1], fill=(0, 0, 0, 255))

        return image

    def generate_lifetime_image(self, width: int, height: int, radius: int) -> Image.Image:
        """
        生成寿命测试图：
        - 左半部分：纯黑
        - 右半部分：纯白
        - 图片正中心绘制一个指定半径的黑色实心圆
        """
        image = Image.new("RGBA", (width, height), (255, 255, 255, 255))
        draw = ImageDraw.Draw(image)

        # 左半区域填充黑色
        half_w = width // 2
        draw.rectangle([0, 0, half_w - 1, height - 1], fill=(0, 0, 0, 255))

        # 以白色区域（右半部分）的中心绘制黑色实心圆
        # 右半区域 x 范围：[half_w, width-1]，其中心 x = half_w + (width - half_w) // 2
        cx = half_w + (width - half_w) // 2
        cy = height // 2
        r = max(1, radius)
        bbox = [cx - r, cy - r, cx + r, cy + r]
        draw.ellipse(bbox, fill=(0, 0, 0, 255))

        return image

    def apply_circle_mask(self, image: Image.Image) -> Image.Image:
        """对图片应用椭圆遮罩，使输出呈圆形（超出范围变为透明）。"""
        width, height = image.size
        mask = Image.new("L", (width, height), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, width - 1, height - 1), fill=255)

        result = image.copy()
        result.putalpha(mask)
        return result

    # ──────────────────────────────────────────────
    # 预览刷新
    # ──────────────────────────────────────────────

    def update_preview(self):
        """刷新右侧预览图，批量模式下同步更新批量列表。"""
        self.batch_list.clear()
        batch_enabled = (
            self.batch_enable.isChecked()
            and self.type_combo.currentText() == "黑底白圆图（10%-100%）"
        )

        if batch_enabled:
            values = self.get_batch_percentages()
            for p in values:
                self.batch_list.addItem(QListWidgetItem(f"{p}%"))
            image = self.generate_image(percentage=values[0])
        else:
            image = self.generate_image()

        self.preview_image = image
        self.show_pil_image(image)

    def show_pil_image(self, image: Image.Image):
        """将 PIL 图片缩放后显示在预览标签中，保持宽高比。"""
        qimage = ImageQt.ImageQt(image)
        pixmap = QPixmap.fromImage(qimage)
        scaled = pixmap.scaled(
            640, 640,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.preview_label.setPixmap(scaled)

    # ──────────────────────────────────────────────
    # 保存 / 导出
    # ──────────────────────────────────────────────

    def save_single_image(self):
        """弹出保存对话框，将当前预览图保存为单张文件。"""
        image = self.generate_image()
        img_format = self.format_combo.currentText()
        suffix = img_format.lower() if img_format != "JPEG" else "jpg"

        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存图片", f"output.{suffix}", f"图片文件 (*.{suffix})"
        )
        if not file_path:
            return

        self._save_image_with_format(image, file_path, img_format)
        QMessageBox.information(self, "完成", "图片已保存。")

    def save_batch_images(self):
        """批量导出黑底白圆图（需启用批量生成且当前类型正确）。"""
        if not (self.batch_enable.isChecked()
                and self.type_combo.currentText() == "黑底白圆图（10%-100%）"):
            QMessageBox.warning(
                self, "提示", '批量导出仅用于"黑底白圆图（10%-100%）"且需启用批量生成。'
            )
            return

        folder = QFileDialog.getExistingDirectory(self, "选择导出文件夹")
        if not folder:
            return

        img_format = self.format_combo.currentText()
        suffix = img_format.lower() if img_format != "JPEG" else "jpg"
        values = self.get_batch_percentages()

        for p in values:
            image = self.generate_image(percentage=p)
            file_path = os.path.join(folder, f"circle_{p}.{suffix}")
            self._save_image_with_format(image, file_path, img_format)

        QMessageBox.information(self, "完成", f"已批量导出 {len(values)} 张图片。")

    def save_batch_gray_images(self):
        """
        批量导出 WRGB 灰阶图。
        按批量设置的起始值/结束值/步长遍历，
        勾选"导出全部通道"时对 WRGB 四个通道各自生成全套图片。
        文件命名格式：{通道}_{值:03d}.{后缀}，例如 R_128.png
        """
        if self.type_combo.currentText() != "WRGB不同灰阶图片":
            QMessageBox.warning(self, "提示", '批量导出灰阶图仅用于"WRGB不同灰阶图片"类型。')
            return

        folder = QFileDialog.getExistingDirectory(self, "选择导出文件夹")
        if not folder:
            return

        width = self.width_spin.value()
        height = self.height_spin.value()
        shape = self.shape_combo.currentText()
        img_format = self.format_combo.currentText()
        suffix = img_format.lower() if img_format != "JPEG" else "jpg"

        start = self.gray_batch_start_spin.value()
        end = self.gray_batch_end_spin.value()
        step = self.gray_batch_step_spin.value()
        if start > end:
            start, end = end, start
        values = list(range(start, end + 1, step))

        # 全部通道 or 仅当前通道
        all_channels = self.gray_all_channels_check.isChecked()
        channels = ["W", "R", "G", "B"] if all_channels else [self.gray_channel_combo.currentText()[0]]

        count = 0
        for ch in channels:
            for v in values:
                image = self.generate_wrgb_gray(width, height, ch, v)
                if shape == "圆形图":
                    image = self.apply_circle_mask(image)
                file_path = os.path.join(folder, f"{ch}_{v:03d}.{suffix}")
                self._save_image_with_format(image, file_path, img_format)
                count += 1

        QMessageBox.information(self, "完成", f"已批量导出 {count} 张灰阶图片。")

    def _save_image_with_format(self, image: Image.Image, file_path: str, img_format: str):
        """
        将图片保存为指定格式。
        JPEG 不支持透明通道，RGBA 图片自动合并到白色背景后保存。
        """
        if img_format == "JPEG":
            if image.mode == "RGBA":
                background = Image.new("RGB", image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[-1])
                background.save(file_path, format="JPEG", quality=95)
            else:
                image.convert("RGB").save(file_path, format="JPEG", quality=95)
        else:
            image.save(file_path, format=img_format)


def main():
    app = QApplication(sys.argv)
    window = ImageGeneratorWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
