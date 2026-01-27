# nmr_control.py
from PyQt5.QtWidgets import *
from PyQt5.QtCore import QThread, pyqtSignal
import time


class NMRContinuousReader(QThread):
    """Continuous reader for M0 and T values every 5 seconds"""
    values_ready = pyqtSignal(float, float)  # M0, T
    error = pyqtSignal(str)

    def __init__(self, nmr_instrument):
        super().__init__()
        self.nmr = nmr_instrument
        self._running = True

    def run(self):
        while self._running:
            try:
                time.sleep(2)  # Wait 5 seconds
                m0 = self.nmr.M0()
                t = self.nmr.TmK()
                self.values_ready.emit(m0, t)
            except Exception as e:
                self.error.emit(str(e))
                break

    def stop(self):
        self._running = False


class NMRControlPanel(QGroupBox):
    def __init__(self):
        super().__init__("NMR")
        self.setFixedHeight(150)
        self.nmr = None
        self.reader = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setStretch(0, 0)
        layout.setSpacing(0)

        # Connection
        conn_layout = QHBoxLayout()
        self.addr_input = QLineEdit("GPIB1::22::INSTR")
        self.connect_btn = QPushButton("Connect")
        self.status_label = QLabel("Disconnected")
        conn_layout.addWidget(self.addr_input)
        conn_layout.addWidget(self.connect_btn)
        conn_layout.addWidget(self.status_label)
        layout.addLayout(conn_layout)

        # Readings display
        readings_layout = QHBoxLayout()
        readings_layout.addWidget(QLabel("M0:"))
        self.m0_label = QLabel("N/A")
        readings_layout.addWidget(self.m0_label)

        readings_layout.addWidget(QLabel("T (mK):"))
        self.t_label = QLabel("N/A")
        readings_layout.addWidget(self.t_label)

        self.single_btn = QPushButton("Single")
        self.single_btn.clicked.connect(self.single)
        self.single_btn.setEnabled(False)
        readings_layout.addWidget(self.single_btn)

        self.auto_btn = QPushButton("Auto")
        self.auto_btn.clicked.connect(self.auto)
        self.auto_btn.setEnabled(False)
        readings_layout.addWidget(self.auto_btn)

        layout.addLayout(readings_layout)

        # Known values section
        known_layout = QHBoxLayout()

        # Known M0
        known_m0_layout = QHBoxLayout()
        known_m0_layout.addWidget(QLabel("Known M0:"))
        self.known_m0_input = QLineEdit()
        known_m0_layout.addWidget(self.known_m0_input)
        known_layout.addLayout(known_m0_layout)

        # Known T
        known_t_layout = QHBoxLayout()
        known_t_layout.addWidget(QLabel("Known T:"))
        self.known_t_input = QLineEdit()
        known_t_layout.addWidget(self.known_t_input)
        known_layout.addLayout(known_t_layout)

        # Get and Set buttons
        self.get_known_btn = QPushButton("Get Known")
        self.set_known_btn = QPushButton("Set Known")
        known_layout.addWidget(self.get_known_btn)
        known_layout.addWidget(self.set_known_btn)

        layout.addLayout(known_layout)

        self.setLayout(layout)

        # Connect signals
        self.connect_btn.clicked.connect(self.toggle_connection)
        self.get_known_btn.clicked.connect(self.get_known_values)
        self.set_known_btn.clicked.connect(self.set_known_values)

        # Initial button state
        self.set_buttons_enabled(False)

    def set_buttons_enabled(self, enabled):
        """Enable or disable all buttons"""
        self.get_known_btn.setEnabled(enabled)
        self.set_known_btn.setEnabled(enabled)
        self.known_m0_input.setEnabled(enabled)
        self.known_t_input.setEnabled(enabled)
        self.single_btn.setEnabled(enabled)
        self.auto_btn.setEnabled(enabled)

    def toggle_connection(self):
        if self.connect_btn.text() == "Connect":
            self.connect_nmr()
        else:
            self.disconnect_nmr()

    def connect_nmr(self):
        try:
            from demag_gui.driver.virtual_instruments import NMR
            self.nmr = NMR('nmr', self.addr_input.text())
            # Enable buttons
            self.set_buttons_enabled(True)

            # Start continuous reading
            self.reader = NMRContinuousReader(self.nmr)
            self.reader.values_ready.connect(self.update_readings)
            self.reader.error.connect(self.handle_error)
            self.reader.start()

            # Get initial known values
            self.get_known_values()

            self.connect_btn.setText("Disconnect")
            self.status_label.setText("Connected")

        except Exception as e:
            self.status_label.setText("Failed")
            QMessageBox.warning(self, "Connection Failed", str(e))

    def disconnect_nmr(self):
        if self.reader:
            self.reader.stop()
            self.reader.wait()
            self.reader = None

        if self.nmr:
            self.nmr.close()
            self.nmr = None

        # Disable buttons
        self.set_buttons_enabled(False)

        self.connect_btn.setText("Connect")
        self.status_label.setText("Disconnected")
        self.m0_label.setText("N/A")
        self.t_label.setText("N/A")
        self.known_m0_input.clear()
        self.known_t_input.clear()

    def update_readings(self, m0, t):
        self.m0_label.setText(f"{m0:.3f}")
        self.t_label.setText(f"{t:.2f}")

    def get_known_values(self):
        """Get both Known M0 and Known T at once"""
        if self.nmr:
            try:
                known_m0 = self.nmr.KnownM0_A()
                known_t = self.nmr.KnownT_A()
                self.known_m0_input.setText(f"{known_m0:.3f}")
                self.known_t_input.setText(f"{known_t:.2f}")
            except Exception as e:
                QMessageBox.warning(self, "Get Failed", f"Failed to get known values: {str(e)}")

    def single(self):
        self.nmr.OperationState('Single')

    def auto(self):
        self.nmr.OperationState('Auto')

    def set_known_values(self):
        """Set both Known M0 and Known T at once"""
        if self.nmr:
            try:
                m0_value = float(self.known_m0_input.text())
                t_value = float(self.known_t_input.text())

                self.nmr.set_KnownM0_A(m0_value)
                self.nmr.set_KnownT_A(t_value)

                QMessageBox.information(self, "Success", "Known values set successfully")
            except ValueError:
                QMessageBox.warning(self, "Invalid Input", "Please enter valid numbers")
            except Exception as e:
                QMessageBox.warning(self, "Set Failed", f"Failed to set known values: {str(e)}")

    def handle_error(self, error_msg):
        self.status_label.setText("Error")
        QMessageBox.warning(self, "NMR Error", error_msg)
        self.disconnect_nmr()

    def close(self):
        self.disconnect_nmr()