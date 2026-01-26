# main.py
from PyQt5.QtWidgets import *
import sys
from PyQt5.QtGui import QFont
from PyQt5.QtCore import pyqtSignal, QThread, QObject, Qt
from demag_gui.gui.hs_control import HSControlPanel
from demag_gui.gui.mips_control import MIPSControlPanel
from demag_gui.gui.mct_control import MCTControlPanel
from demag_gui.gui.nmr_control import NMRControlPanel
import threading


class MeasurementWorker(QObject):
    """Measurement worker thread with stop event"""
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._stop_event = threading.Event()

    def setup(self, func_name, mct_panel, nmr_panel, mips_panel, hs_panel):
        """Setup measurement parameters"""
        self.func_name = func_name
        self.mct_panel = mct_panel
        self.nmr_panel = nmr_panel
        self.mips_panel = mips_panel
        self.hs_panel = hs_panel

    def is_stopped(self):
        """Check if measurement should stop"""
        return self._stop_event.is_set()

    def run(self):
        # Try to pass stop callback to measurement function
        from demag_gui.utils.measurements import run_measurement

        # Create stop callback function
        def check_stop():
            return self.is_stopped()

        # Pass stop callback if function supports it
        result = run_measurement(self.func_name, self.mct_panel, self.nmr_panel,
                                 self.mips_panel, self.hs_panel,
                                 stop_callback=check_stop)

        if not self.is_stopped():
            self.finished.emit(f"Completed: {result}")
        else:
            self.finished.emit("Stopped by user")

    def stop(self):
        """Stop measurement"""
        self._stop_event.set()


class InstrumentApp(QWidget):
    def __init__(self):
        super().__init__()
        self.mct_panel = None
        self.nmr_panel = None
        self.mips_panel = None
        self.hs_panel = None
        self.worker_thread = None
        self.worker = None
        self.setup_ui()

    def setup_ui(self):
        font = self.font()
        font.setPointSize(font.pointSize())
        self.setFont(font)

        self.setWindowTitle("Instrument Control")
        main_layout = QVBoxLayout()

        # Instrument panels
        instruments_layout = QHBoxLayout()
        instruments_layout.setSpacing(2)  # 减少间距

        self.mct_panel = MCTControlPanel()
        instruments_layout.addWidget(self.mct_panel, 2)

        right_layout = QVBoxLayout()
        right_layout.setSpacing(4)  # 减少垂直间距

        self.nmr_panel = NMRControlPanel()
        self.mips_panel = MIPSControlPanel()
        self.hs_panel = HSControlPanel()

        right_layout.addWidget(self.nmr_panel, 0)
        right_layout.addWidget(self.mips_panel, 0)
        right_layout.addWidget(self.hs_panel, 0)

        instruments_layout.addLayout(right_layout, 1)
        main_layout.addLayout(instruments_layout)

        # Measurement control
        measurements_group = QGroupBox("Measurement Control")

        # 使用网格布局实现更紧凑的按钮行
        measurements_grid = QGridLayout()
        measurements_grid.setSpacing(4)  # 减少网格间距
        measurements_grid.setContentsMargins(4, 4, 4, 4)  # 减少网格边距

        # 按钮行 - 第一行
        row = 0

        # 更新按钮
        self.update_btn = QPushButton("↻ Update")
        self.update_btn.clicked.connect(self.reload_measurements)
        self.update_btn.setFixedWidth(80)  # 固定宽度
        measurements_grid.addWidget(self.update_btn, row, 0)

        # 测量标签
        measurement_label = QLabel("Measurement:")
        measurement_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        measurements_grid.addWidget(measurement_label, row, 1)

        # 测量下拉框
        self.measurement_combo = QComboBox()
        self.load_measurements()
        measurements_grid.addWidget(self.measurement_combo, row, 2, 1, 2)  # 跨2列

        # 运行按钮
        self.run_btn = QPushButton("▶ Run")
        self.run_btn.clicked.connect(self.run_selected_measurement)
        self.run_btn.setFixedWidth(80)
        measurements_grid.addWidget(self.run_btn, row, 4)

        # 停止按钮
        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.clicked.connect(self.stop_measurement)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setFixedWidth(80)
        measurements_grid.addWidget(self.stop_btn, row, 5)

        # 第二行：状态显示
        row = 1

        # 错误标签
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: red;")
        self.error_label.setWordWrap(True)
        self.error_label.setMaximumHeight(40)  # 限制高度
        measurements_grid.addWidget(self.error_label, row, 0, 1, 3)  # 跨3列

        # 状态标签
        self.measurement_status = QLabel("Ready")
        self.measurement_status.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        measurements_grid.addWidget(self.measurement_status, row, 3, 1, 3)  # 跨3列

        # 设置列宽比例
        measurements_grid.setColumnStretch(0, 0)  # 更新按钮
        measurements_grid.setColumnStretch(1, 0)  # 标签
        measurements_grid.setColumnStretch(2, 1)  # 下拉框
        measurements_grid.setColumnStretch(3, 1)  # 下拉框的延伸
        measurements_grid.setColumnStretch(4, 0)  # 运行按钮
        measurements_grid.setColumnStretch(5, 0)  # 停止按钮

        measurements_group.setLayout(measurements_grid)
        main_layout.addWidget(measurements_group)

        self.setLayout(main_layout)
        self.setMinimumSize(1400, 800)  # 稍微减小最小尺寸

    def reload_measurements(self):
        """Reload measurement list"""
        self.load_measurements()
        self.measurement_status.setText("Updated")
        self.clear_error()

    def load_measurements(self):
        """Load available measurements"""
        from demag_gui.utils.measurements import get_all_measurements
        measurements, _ = get_all_measurements()
        self.measurement_combo.clear()
        for name, desc in measurements:
            self.measurement_combo.addItem(f"{name}", name)

    def run_selected_measurement(self):
        """Run selected measurement"""
        if self.measurement_combo.currentIndex() < 0:
            self.show_error("Select a measurement")
            return

        func_name = self.measurement_combo.currentData()
        if not func_name:
            return

        self.clear_error()
        self.measurement_status.setText("Running...")

        # Clean up existing thread
        self.cleanup_thread()

        # Create new worker
        self.worker = MeasurementWorker()
        self.worker.setup(func_name, self.mct_panel, self.nmr_panel,
                          self.mips_panel, self.hs_panel)

        # Create and start thread
        self.worker_thread = QThread()
        self.worker.moveToThread(self.worker_thread)

        # Connect signals
        self.worker_thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_measurement_finished)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.error.connect(self.on_measurement_error)
        self.worker.error.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(self.on_thread_finished)

        # Start thread
        self.worker_thread.start()

        # Update UI state
        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

    def stop_measurement(self):
        """Stop current measurement"""
        if self.worker:
            self.worker.stop()
            self.measurement_status.setText("Stopping...")
            self.show_error("Stopping measurement... Please wait")
            self.stop_btn.setEnabled(False)
            self.show_error("Measurement stopped")

    def on_measurement_finished(self, result):
        """Handle measurement completion"""
        self.measurement_status.setText(result)

    def on_measurement_error(self, error_msg):
        """Handle measurement error"""
        self.show_error(error_msg)
        self.measurement_status.setText("Error")

    def on_thread_finished(self):
        """Handle thread completion"""
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.cleanup_thread()

    def cleanup_thread(self):
        """Clean up worker thread"""
        if self.worker_thread:
            if self.worker_thread.isRunning():
                self.worker_thread.quit()
                self.worker_thread.wait(100)
            self.worker_thread = None

        if self.worker:
            self.worker = None

    def show_error(self, message):
        """Display error message"""
        self.error_label.setText(message)

    def clear_error(self):
        """Clear error message"""
        self.error_label.clear()

    def closeEvent(self, event):
        """Clean up on window close"""
        self.stop_measurement()

        for panel in [self.mct_panel, self.nmr_panel, self.mips_panel, self.hs_panel]:
            if hasattr(panel, 'close'):
                panel.close()

        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    font = QFont("Arial")
    font.setPointSize(font.pointSize())
    app.setFont(font)

    window = InstrumentApp()
    window.show()
    sys.exit(app.exec_())