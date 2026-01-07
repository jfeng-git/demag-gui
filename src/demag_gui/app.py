# main.py
from PyQt5.QtWidgets import *
import sys
from PyQt5.QtGui import QFont
from demag_gui.gui.hs_control import HSControlPanel
from demag_gui.gui.mips_control import MIPSControlPanel
from demag_gui.gui.mct_control import MCTControlPanel
from demag_gui.gui.nmr_control import NMRControlPanel


class InstrumentApp(QWidget):
    def __init__(self):
        super().__init__()
        self.mct_panel = None
        self.nmr_panel = None
        self.mips_panel = None
        self.hs_panel = None
        self.setup_ui()

    def setup_ui(self):
        font = self.font()
        font.setPointSize(font.pointSize() + 2)
        self.setFont(font)

        self.setWindowTitle("Instrument Control")
        main_layout = QVBoxLayout()

        # Instrument panels
        instruments_layout = QHBoxLayout()
        self.mct_panel = MCTControlPanel()
        instruments_layout.addWidget(self.mct_panel, 2)

        right_layout = QVBoxLayout()
        self.nmr_panel = NMRControlPanel()
        self.mips_panel = MIPSControlPanel()
        self.hs_panel = HSControlPanel()
        right_layout.addWidget(self.nmr_panel)
        right_layout.addWidget(self.mips_panel)
        right_layout.addWidget(self.hs_panel)
        instruments_layout.addLayout(right_layout, 1)
        main_layout.addLayout(instruments_layout)

        # Measurement control
        measurements_group = QGroupBox("Measurement Control")
        measurements_layout = QHBoxLayout()

        self.update_btn = QPushButton("↻ Update")
        self.update_btn.clicked.connect(self.reload_measurements)
        measurements_layout.addWidget(self.update_btn)

        measurements_layout.addWidget(QLabel("Measurement:"))
        self.measurement_combo = QComboBox()
        self.load_measurements()
        measurements_layout.addWidget(self.measurement_combo)

        self.run_btn = QPushButton("▶ Run")
        self.run_btn.clicked.connect(self.run_selected_measurement)
        measurements_layout.addWidget(self.run_btn)

        self.measurement_status = QLabel("Ready")
        measurements_layout.addWidget(self.measurement_status)
        measurements_layout.addStretch()

        measurements_group.setLayout(measurements_layout)
        main_layout.addWidget(measurements_group)

        self.setLayout(main_layout)
        self.setMinimumSize(1800, 1000)

    def reload_measurements(self):
        self.load_measurements()
        self.measurement_status.setText("Updated")

    def load_measurements(self):
        try:
            from GUI_Demag.src.GUI_Demag.Tools.measurements import get_all_measurements
            measurements, _ = get_all_measurements()
            self.measurement_combo.clear()
            for name, desc in measurements:
                self.measurement_combo.addItem(f"{name}: {desc}", name)
        except:
            self.measurement_combo.clear()
            self.measurement_combo.addItem("No measurements")

    def run_selected_measurement(self):
        if self.measurement_combo.currentIndex() < 0:
            QMessageBox.warning(self, "No Selection", "Select a measurement")
            return

        func_name = self.measurement_combo.currentData()
        if not func_name:
            return

        # Run in thread
        import threading
        def run_in_thread():
            from GUI_Demag.src.GUI_Demag.Tools.measurements import run_measurement
            result = run_measurement(func_name, self.mct_panel, self.nmr_panel, self.mips_panel, self.hs_panel)
            self.measurement_status.setText(result)

        self.run_btn.setEnabled(False)
        thread = threading.Thread(target=run_in_thread)
        thread.daemon = True
        thread.start()
        self.run_btn.setEnabled(True)

    def closeEvent(self, event):
        for panel in [self.mct_panel, self.nmr_panel, self.mips_panel, self.hs_panel]:
            if hasattr(panel, 'close'):
                try:
                    panel.close()
                except:
                    pass
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    font = QFont("Arial")
    font.setPointSize(font.pointSize() + 2)
    app.setFont(font)

    window = InstrumentApp()
    window.show()
    sys.exit(app.exec_())