# hs_control.py
from PyQt5 import Qt
from PyQt5.QtWidgets import *
from PyQt5.QtCore import QThread, pyqtSignal

class HSReadingThread(QThread):
    reading_ready = pyqtSignal(float, str, str)  # current, output_state, heater_state
    reading_error = pyqtSignal(str)

    def __init__(self, hs_instrument):
        super().__init__()
        self.hs = hs_instrument
        self._is_running = True

    def run(self):
        while self._is_running:
            try:
                current = self.hs.I()
                output_state = "on" if hasattr(self.hs, 'output_state') else "Unknown"
                heater_state = "on" if hasattr(self.hs, 'heater_state') else "Unknown"

                self.reading_ready.emit(current, output_state, heater_state)
                self.msleep(1000)
            except Exception as e:
                self.reading_error.emit(str(e))
                break

    def stop(self):
        self._is_running = False
        self.wait()

class HSControlPanel(QGroupBox):
    def __init__(self):
        super().__init__("HS")
        self.hs_instrument = None
        self.hs_thread = None
        self.setFixedHeight(120)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(2)

        # Connection row
        conn_hbox = QHBoxLayout()
        self.addr_input = QLineEdit("ASRL3::INSTR")
        self.connect_btn = QPushButton("Connect")
        self.status_label = QLabel("Disconnected")
        self.status_label.setStyleSheet("color: gray")

        self.connect_btn.clicked.connect(self.toggle_connection)

        conn_hbox.addWidget(self.addr_input)
        conn_hbox.addWidget(self.connect_btn)
        conn_hbox.addWidget(self.status_label)
        layout.addLayout(conn_hbox)

        controls_hbox = QHBoxLayout()

        # Current display
        current_label = QLabel("Current:")
        current_label.setFixedWidth(60)
        controls_hbox.addWidget(current_label)
        self.current_display = QLineEdit("Unknown")
        self.current_display.setReadOnly(True)
        self.current_display.setFixedWidth(80)  # 约7字符宽度
        font_size = self.font().pointSize()
        self.current_display.setStyleSheet(f"font-weight: bold; color: blue; font-size: {font_size}pt;")
        controls_hbox.addWidget(self.current_display)
        controls_hbox.addSpacing(40)

        # Output button
        output_label = QLabel("Output:")
        output_label.setFixedWidth(60)
        controls_hbox.addWidget(output_label)
        self.output_btn = QPushButton("Unknown")
        self.output_btn.clicked.connect(self.toggle_output)
        self.output_btn.setEnabled(False)
        self.output_btn.setFixedWidth(60)  # ON/OFF 宽度
        self.output_btn.setStyleSheet(f"font-size: {font_size}pt;")
        controls_hbox.addWidget(self.output_btn)
        controls_hbox.addSpacing(40)

        # Heater switch button
        heater_label = QLabel("Heater:")
        heater_label.setFixedWidth(60)
        controls_hbox.addWidget(heater_label)
        self.heater_btn = QPushButton("Unknown")
        self.heater_btn.clicked.connect(self.toggle_heater)
        self.heater_btn.setEnabled(False)
        self.heater_btn.setFixedWidth(60)  # ON/OFF 宽度
        self.heater_btn.setStyleSheet(f"font-size: {font_size}pt;")
        controls_hbox.addWidget(self.heater_btn)

        layout.addLayout(controls_hbox)

        self.setLayout(layout)

    def toggle_connection(self):
        if self.connect_btn.text() == "Connect":
            self.connect_hs()
        else:
            self.disconnect_hs()

    def connect_hs(self):
        str_input = self.addr_input.text()
        try:
            from demag_gui.driver.UDP5303 import UDP5303
            self.hs_instrument = UDP5303('HeatSwitch', str_input)

            self.output_btn.setEnabled(True)
            self.heater_btn.setEnabled(True)

            self.hs_thread = HSReadingThread(self.hs_instrument)
            self.hs_thread.reading_ready.connect(self.update_readings)
            self.hs_thread.reading_error.connect(self.handle_reading_error)
            self.hs_thread.start()

            self.connect_btn.setText("Disconnect")
            self.status_label.setText("Running")
            self.status_label.setStyleSheet("color: green")

        except Exception as e:
            QMessageBox.critical(self, "Connection Failed", f"Failed to connect to HS: {str(e)}")
            self.status_label.setText("Failed")
            self.status_label.setStyleSheet("color: red")

    def disconnect_hs(self):
        try:
            if self.hs_thread:
                self.hs_thread.stop()
                self.hs_thread = None

            if self.hs_instrument:
                self.hs_instrument.close()
                self.hs_instrument = None

            self.output_btn.setEnabled(False)
            self.heater_btn.setEnabled(False)

            self.current_display.setText("Unknown")
            self.output_btn.setText("Unknown")
            self.heater_btn.setText("Unknown")

            self.connect_btn.setText("Connect")
            self.status_label.setText("Disconnected")
            self.status_label.setStyleSheet("color: gray")

        except Exception as e:
            QMessageBox.critical(self, "Disconnect Failed", f"Failed to disconnect from HS: {str(e)}")

    def toggle_output(self):
        if not self.hs_instrument:
            return

        try:
            current_text = self.output_btn.text().lower()
            if current_text == "on":
                self.hs_instrument.Output('off')
                self.output_btn.setText("OFF")
                self.output_btn.setStyleSheet("background-color: lightgray;")
            else:
                self.hs_instrument.Output('on')
                self.output_btn.setText("ON")
                self.output_btn.setStyleSheet("background-color: lightgreen;")

        except Exception as e:
            QMessageBox.warning(self, "Output Error", f"Failed to toggle output: {str(e)}")

    def toggle_heater(self):
        pass
    #     if not self.hs_instrument:
    #         return

    #     try:
    #         current_text = self.heater_btn.text().lower()
    #         if current_text == "on":
    #             self.hs_instrument.set_HS('off')
    #             self.heater_btn.setText("OFF")
    #             self.heater_btn.setStyleSheet("background-color: lightgray;")
    #         else:
    #             self.hs_instrument.set_HS('on')
    #             self.heater_btn.setText("ON")
    #             self.heater_btn.setStyleSheet("background-color: lightgreen;")

    #     except Exception as e:
    #         QMessageBox.warning(self, "Heater Error", f"Failed to toggle heater: {str(e)}")

    def update_readings(self, current, output_state, heater_state):
        self.current_display.setText(f"{current:.3f} A")

        if output_state == "on":
            self.output_btn.setText("ON")
            self.output_btn.setStyleSheet("background-color: lightgreen;")
        elif output_state == "off":
            self.output_btn.setText("OFF")
            self.output_btn.setStyleSheet("background-color: lightgray;")

        if heater_state == "on":
            self.heater_btn.setText("ON")
            self.heater_btn.setStyleSheet("background-color: lightgreen;")
        elif heater_state == "off":
            self.heater_btn.setText("OFF")
            self.heater_btn.setStyleSheet("background-color: lightgray;")

        if self.hs_thread:
            self.hs_thread = HSReadingThread(self.hs_instrument)
            self.hs_thread.reading_ready.connect(self.update_readings)
            self.hs_thread.reading_error.connect(self.handle_reading_error)
            self.hs_thread.start()

    def handle_reading_error(self, error_msg):
        QMessageBox.warning(self, "HS Reading Error", f"Error reading HS values: {str(error_msg)}")
        self.current_display.setText("Error")

        if self.hs_instrument:
            self.hs_thread = HSReadingThread(self.hs_instrument)
            self.hs_thread.reading_ready.connect(self.update_readings)
            self.hs_thread.reading_error.connect(self.handle_reading_error)
            self.hs_thread.start()

    def close(self):
        if self.hs_thread:
            self.hs_thread.stop()