from PyQt5.QtWidgets import QWidget, QPushButton, QFrame, QGraphicsDropShadowEffect
from PyQt5.QtCore import QPropertyAnimation, QVariantAnimation, QEasingCurve, QParallelAnimationGroup, QPoint, Qt
from PyQt5.QtGui import QPainter, QColor, QFont, QPen

class AnimatedStackedWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._widgets = []
        self._current_index = -1
        self._animation_duration = 280
        self._easing_curve = QEasingCurve.OutQuad
        self._animation_type = "slide_horizontal"  # "slide_horizontal", "fade", "none"
        self._is_animating = False
        self._anim_group = None

    def set_animation_type(self, anim_type):
        self._animation_type = anim_type

    def addWidget(self, widget):
        widget.setParent(self)
        self._widgets.append(widget)
        if self._current_index == -1:
            self._current_index = 0
            widget.setGeometry(self.rect())
            widget.show()
        else:
            widget.hide()
        return len(self._widgets) - 1

    def count(self):
        return len(self._widgets)

    def widget(self, index):
        if 0 <= index < len(self._widgets):
            return self._widgets[index]
        return None

    def indexOf(self, widget):
        try:
            return self._widgets.index(widget)
        except ValueError:
            return -1

    def currentIndex(self):
        return self._current_index

    def currentWidget(self):
        return self.widget(self._current_index)

    def setCurrentWidget(self, widget):
        idx = self.indexOf(widget)
        if idx != -1:
            self.setCurrentIndex(idx)

    def setCurrentIndex(self, index):
        if not (0 <= index < len(self._widgets)):
            return
        if index == self._current_index:
            return
        self.slide_to_index(index)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = self.width()
        h = self.height()
        if not self._is_animating:
            for i, wdg in enumerate(self._widgets):
                if i == self._current_index:
                    wdg.setGeometry(0, 0, w, h)
                    wdg.show()
                else:
                    wdg.hide()
        else:
            # Nếu đang chạy animation mà bị resize đột ngột, dừng hoạt ảnh và fit widget
            if self._anim_group:
                self._anim_group.stop()
            self._is_animating = False
            for i, wdg in enumerate(self._widgets):
                wdg.setGraphicsEffect(None)
                if i == self._current_index:
                    wdg.setGeometry(0, 0, w, h)
                    wdg.show()
                else:
                    wdg.hide()

    def slide_to_index(self, index):
        if self._is_animating:
            if self._anim_group:
                self._anim_group.stop()
            self._is_animating = False
            self._on_animation_finished(index)
            return

        old_idx = self._current_index
        new_idx = index

        if old_idx == -1:
            self._current_index = new_idx
            w = self.widget(new_idx)
            if w:
                w.setGeometry(self.rect())
                w.show()
            return

        old_widget = self.widget(old_idx)
        new_widget = self.widget(new_idx)
        if not old_widget or not new_widget:
            self._current_index = new_idx
            if new_widget:
                new_widget.setGeometry(self.rect())
                new_widget.show()
            return

        self._is_animating = True
        w = self.width()
        h = self.height()

        # Đặt vị trí hiển thị ban đầu
        new_widget.setGeometry(0, 0, w, h)
        new_widget.show()
        new_widget.raise_()

        self._anim_group = QParallelAnimationGroup()
        self._anim_group.finished.connect(lambda: self._on_animation_finished(new_idx))

        if self._animation_type == "none":
            self._on_animation_finished(new_idx)
            return

        elif self._animation_type == "fade":
            from PyQt5.QtWidgets import QGraphicsOpacityEffect
            
            eff_new = QGraphicsOpacityEffect(new_widget)
            new_widget.setGraphicsEffect(eff_new)
            anim_new = QPropertyAnimation(eff_new, b"opacity")
            anim_new.setDuration(self._animation_duration)
            anim_new.setStartValue(0.0)
            anim_new.setEndValue(1.0)
            anim_new.setEasingCurve(self._easing_curve)
            self._anim_group.addAnimation(anim_new)

            eff_old = QGraphicsOpacityEffect(old_widget)
            old_widget.setGraphicsEffect(eff_old)
            anim_old = QPropertyAnimation(eff_old, b"opacity")
            anim_old.setDuration(self._animation_duration)
            anim_old.setStartValue(1.0)
            anim_old.setEndValue(0.0)
            anim_old.setEasingCurve(self._easing_curve)
            self._anim_group.addAnimation(anim_old)

        elif self._animation_type == "slide_horizontal":
            # Hoạt ảnh lai Parallax Slide + Fade mượt mà vượt trội
            from PyQt5.QtWidgets import QGraphicsOpacityEffect
            
            # 1. Hoạt ảnh mờ tỏ chéo (Opacity Cross-fade)
            eff_new = QGraphicsOpacityEffect(new_widget)
            new_widget.setGraphicsEffect(eff_new)
            anim_op_new = QPropertyAnimation(eff_new, b"opacity")
            anim_op_new.setDuration(self._animation_duration)
            anim_op_new.setStartValue(0.0)
            anim_op_new.setEndValue(1.0)
            anim_op_new.setEasingCurve(self._easing_curve)
            self._anim_group.addAnimation(anim_op_new)

            eff_old = QGraphicsOpacityEffect(old_widget)
            old_widget.setGraphicsEffect(eff_old)
            anim_op_old = QPropertyAnimation(eff_old, b"opacity")
            anim_op_old.setDuration(self._animation_duration)
            anim_op_old.setStartValue(1.0)
            anim_op_old.setEndValue(0.0)
            anim_op_old.setEasingCurve(self._easing_curve)
            self._anim_group.addAnimation(anim_op_old)

            # 2. Hoạt ảnh dịch chuyển vị trí nhẹ (Subtle Parallax Slide - 15% width)
            offset = int(w * 0.15)
            start_x = offset if new_idx > old_idx else -offset
            new_widget.move(start_x, 0)

            anim_pos_new = QPropertyAnimation(new_widget, b"pos")
            anim_pos_new.setDuration(self._animation_duration)
            anim_pos_new.setStartValue(QPoint(start_x, 0))
            anim_pos_new.setEndValue(QPoint(0, 0))
            anim_pos_new.setEasingCurve(self._easing_curve)
            self._anim_group.addAnimation(anim_pos_new)

            anim_pos_old = QPropertyAnimation(old_widget, b"pos")
            anim_pos_old.setDuration(self._animation_duration)
            anim_pos_old.setStartValue(QPoint(0, 0))
            anim_pos_old.setEndValue(QPoint(-start_x, 0))
            anim_pos_old.setEasingCurve(self._easing_curve)
            self._anim_group.addAnimation(anim_pos_old)

        self._anim_group.start()

    def _on_animation_finished(self, new_idx):
        self._is_animating = False
        self._current_index = new_idx
        w = self.width()
        h = self.height()
        for i, wdg in enumerate(self._widgets):
            if wdg:
                wdg.setGraphicsEffect(None)
                if i == new_idx:
                    wdg.setGeometry(0, 0, w, h)
                    wdg.show()
                else:
                    wdg.hide()


class AnimatedNavButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setFixedHeight(50)
        self.setCursor(Qt.PointingHandCursor)

        # Trạng thái animation (0.0 -> 1.0)
        self._hover_progress = 0.0
        self._check_progress = 0.0

        # Khởi tạo các bộ hoạt ảnh biến
        self._hover_anim = QVariantAnimation(self)
        self._hover_anim.setDuration(180)
        self._hover_anim.setStartValue(0.0)
        self._hover_anim.setEndValue(1.0)
        self._hover_anim.valueChanged.connect(self._update_hover)

        self._check_anim = QVariantAnimation(self)
        self._check_anim.setDuration(220)
        self._check_anim.setStartValue(0.0)
        self._check_anim.setEndValue(1.0)
        self._check_anim.valueChanged.connect(self._update_check)

    def _update_hover(self, val):
        self._hover_progress = val
        self.update()

    def _update_check(self, val):
        self._check_progress = val
        self.update()

    def enterEvent(self, event):
        self._hover_anim.setDirection(QVariantAnimation.Forward)
        self._hover_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover_anim.setDirection(QVariantAnimation.Backward)
        self._hover_anim.start()
        super().leaveEvent(event)

    def nextCheckState(self):
        old = self.isChecked()
        super().nextCheckState()
        if self.isChecked() != old:
            self._animate_check()

    def setChecked(self, checked):
        if self.isChecked() == checked:
            return
        super().setChecked(checked)
        self._animate_check()

    def _animate_check(self):
        if self.isChecked():
            self._check_anim.setDirection(QVariantAnimation.Forward)
        else:
            self._check_anim.setDirection(QVariantAnimation.Backward)
        self._check_anim.start()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        r = self.rect()

        # 1. Vẽ nền
        if self._check_progress > 0.0:
            # Màu checked: Xanh trời dịu nhẹ bán trong suốt (alpha max 45)
            bg_color = QColor(14, 165, 233, int(self._check_progress * 45))
            p.setBrush(bg_color)
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(r.adjusted(4, 2, -4, -2), 8, 8)
        elif self._hover_progress > 0.0:
            # Màu hover: Nền xám đen nhạt #1e293b
            bg_color = QColor(30, 41, 59, int(self._hover_progress * 255))
            p.setBrush(bg_color)
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(r.adjusted(4, 2, -4, -2), 8, 8)

        # 2. Vẽ thanh chỉ báo hoạt động bên trái (Màu Cam Neon)
        if self._check_progress > 0.0:
            ind_height = int(24 * self._check_progress)
            ind_y = (r.height() - ind_height) // 2
            p.setBrush(QColor("#f97316"))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(8, ind_y, 4, ind_height, 2, 2)

        # 3. Vẽ chữ
        font = QFont("Segoe UI", 10)
        font.setBold(self.isChecked())
        p.setFont(font)

        # Đổi màu chữ theo trạng thái
        color_diff = int((248 - 203) * max(self._hover_progress, self._check_progress))
        text_color = QColor(203 + color_diff, 203 + color_diff, 203 + color_diff)
        p.setPen(text_color)

        text_rect = r.adjusted(24, 0, -10, 0)
        p.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, self.text())


class HoverCardFrame(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_StyledBackground, True)

        # Tạo bóng đổ
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(15)
        self._shadow.setColor(QColor(0, 0, 0, 150))
        self._shadow.setOffset(0, 4)
        self.setGraphicsEffect(self._shadow)

        # Hoạt ảnh bóng đổ
        self._blur_anim = QPropertyAnimation(self._shadow, b"blurRadius")
        self._blur_anim.setDuration(220)
        self._blur_anim.setEasingCurve(QEasingCurve.OutQuad)

    def enterEvent(self, event):
        self._blur_anim.setStartValue(15)
        self._blur_anim.setEndValue(28)
        self._shadow.setColor(QColor(249, 115, 22, 100))  # Phát sáng màu Cam Neon nhẹ
        self._shadow.setOffset(0, 6)
        self._blur_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._blur_anim.setStartValue(28)
        self._blur_anim.setEndValue(15)
        self._shadow.setColor(QColor(0, 0, 0, 150))  # Trở lại bóng tối mặc định
        self._shadow.setOffset(0, 4)
        self._blur_anim.start()
        super().leaveEvent(event)
