# mips_control.py (modified heater switch and added checks)
from PyQt5.QtWidgets import *
from PyQt5.QtCore import QThread, pyqtSignal


class MIPSReadingThread(QThread):
    """Thread for reading MIPS instrument data continuously"""
    mips_reading_ready = pyqtSignal(float, float, str, str, float,
                                    float)  # persistent field, output field, ramp status, heater switch, target field, rate
    mips_reading_error = pyqtSignal(str)  # Error signal

    def __init__(self, mips_instrument):
        super().__init__()
        self.mips = mips_instrument  # MIPS instrument instance
        self._is_running = True  # Thread running flag

    def run(self):
        """Main thread execution - read data every 500ms"""
        while self._is_running:
            try:
                # Read all required parameters from instrument
                field_persistent = self.mips.GRPZ.field_persistent()
                field_output = self.mips.GRPZ.field()
                ramp_status = self.mips.GRPZ.ramp_status()
                heater_switch = self.mips.GRPZ.heater_switch()
                field_target_cv = self.mips.GRPZ.field_target()
                field_rate_cv = self.mips.GRPZ.field_ramp_rate() * 60  # Convert to T/min

                # Emit data to main thread
                self.mips_reading_ready.emit(
                    field_persistent, field_output, ramp_status, heater_switch,
                    field_target_cv, field_rate_cv
                )
                self.msleep(500)  # Wait 500ms
            except Exception as e:
                self.mips_reading_error.emit(str(e))
                break

    def stop(self):
        """Stop the reading thread"""
        self._is_running = False
        self.wait()


class MIPSControlPanel(QGroupBox):
    """MIPS instrument control panel with ramp control buttons"""

    def __init__(self):
        super().__init__("MIPS")
        self.mips_instrument = None  # MIPS instrument instance
        self.mips_thread = None  # Reading thread instance
        self.setFixedHeight(320)  # Increased height for new buttons

        self.setup_ui()

    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout()

        # Connection row
        conn_hbox = QHBoxLayout()
        self.addr_input = QLineEdit("TCPIP0::10.18.18.9::7020::SOCKET")
        self.connect_btn = QPushButton("Connect")
        self.status_label = QLabel("Disconnected")
        self.status_label.setStyleSheet("color: gray")

        self.connect_btn.clicked.connect(self.toggle_connection)

        conn_hbox.addWidget(self.addr_input)
        conn_hbox.addWidget(self.connect_btn)
        conn_hbox.addWidget(self.status_label)
        layout.addLayout(conn_hbox)

        # Field control section
        field_group = QGroupBox("Field Control")
        field_layout = QVBoxLayout()
        field_layout.setSpacing(2)

        # Field displays: Bpersistent and Bout
        field_display_hbox = QHBoxLayout()

        # Bpersistent display
        bpersistent_hbox = QHBoxLayout()
        bpersistent_hbox.addWidget(QLabel("Bpersistent (T):"))
        self.bpersistent_display = QLineEdit("Unknown")
        self.bpersistent_display.setReadOnly(True)
        self.bpersistent_display.setMinimumWidth(120)
        font_size = self.font().pointSize()
        self.bpersistent_display.setStyleSheet(f"font-weight: bold; color: blue; font-size: {font_size}pt;")
        bpersistent_hbox.addWidget(self.bpersistent_display)
        field_display_hbox.addLayout(bpersistent_hbox)

        # Bout display
        bout_hbox = QHBoxLayout()
        bout_hbox.addWidget(QLabel("Bout (T):"))
        self.bout_display = QLineEdit("Unknown")
        self.bout_display.setReadOnly(True)
        self.bout_display.setMinimumWidth(120)
        self.bout_display.setStyleSheet(f"font-weight: bold; color: green; font-size: {font_size}pt;")
        bout_hbox.addWidget(self.bout_display)
        field_display_hbox.addLayout(bout_hbox)

        field_layout.addLayout(field_display_hbox)

        # Target field: CV and SV
        target_hbox = QHBoxLayout()

        # Target CV display
        target_cv_hbox = QHBoxLayout()
        target_cv_hbox.addWidget(QLabel("Target CV (T):"))
        self.target_cv_display = QLineEdit("Unknown")
        self.target_cv_display.setReadOnly(True)
        self.target_cv_display.setMinimumWidth(100)
        self.target_cv_display.setStyleSheet(f"font-size: {font_size}pt;")
        target_cv_hbox.addWidget(self.target_cv_display)
        target_hbox.addLayout(target_cv_hbox)

        # Target SV input
        target_sv_hbox = QHBoxLayout()
        target_sv_hbox.addWidget(QLabel("Target SV (T):"))
        self.target_sv_input = QLineEdit("0")
        self.target_sv_input.setMinimumWidth(100)
        self.target_sv_input.setStyleSheet(f"font-size: {font_size}pt;")
        self.target_sv_input.setEnabled(False)
        target_sv_hbox.addWidget(self.target_sv_input)

        self.set_target_btn = QPushButton("Set")
        self.set_target_btn.clicked.connect(self.set_field_target)
        self.set_target_btn.setEnabled(False)
        target_sv_hbox.addWidget(self.set_target_btn)

        target_hbox.addLayout(target_sv_hbox)
        field_layout.addLayout(target_hbox)

        # Rate: CV and SV
        rate_hbox = QHBoxLayout()

        # Rate CV display
        rate_cv_hbox = QHBoxLayout()
        rate_cv_hbox.addWidget(QLabel("Rate CV (T/min):"))
        self.rate_cv_display = QLineEdit("Unknown")
        self.rate_cv_display.setReadOnly(True)
        self.rate_cv_display.setMinimumWidth(100)
        self.rate_cv_display.setStyleSheet(f"font-size: {font_size}pt;")
        rate_cv_hbox.addWidget(self.rate_cv_display)
        rate_hbox.addLayout(rate_cv_hbox)

        # Rate SV input
        rate_sv_hbox = QHBoxLayout()
        rate_sv_hbox.addWidget(QLabel("Rate SV (T/min):"))
        self.rate_sv_input = QLineEdit("0")
        self.rate_sv_input.setMinimumWidth(100)
        self.rate_sv_input.setStyleSheet(f"font-size: {font_size}pt;")
        self.rate_sv_input.setEnabled(False)
        rate_sv_hbox.addWidget(self.rate_sv_input)

        self.set_rate_btn = QPushButton("Set")
        self.set_rate_btn.clicked.connect(self.set_field_rate)
        self.set_rate_btn.setEnabled(False)
        rate_sv_hbox.addWidget(self.set_rate_btn)

        rate_hbox.addLayout(rate_sv_hbox)
        field_layout.addLayout(rate_hbox)

        # Ramp status and heater switch
        status_hbox = QHBoxLayout()

        # Ramp status display
        ramp_hbox = QHBoxLayout()
        ramp_hbox.addWidget(QLabel("Ramp Status:"))
        self.ramp_display = QLineEdit("Unknown")
        self.ramp_display.setReadOnly(True)
        self.ramp_display.setMinimumWidth(150)
        self.ramp_display.setStyleSheet(f"font-weight: bold; font-size: {font_size}pt;")
        ramp_hbox.addWidget(self.ramp_display)
        status_hbox.addLayout(ramp_hbox)

        # Heater switch button
        heater_hbox = QHBoxLayout()
        heater_hbox.addWidget(QLabel("Heater Switch:"))
        self.heater_btn = QPushButton("Unknown")
        self.heater_btn.clicked.connect(self.toggle_heater)
        self.heater_btn.setEnabled(False)
        self.heater_btn.setMinimumWidth(150)
        self.heater_btn.setStyleSheet(f"font-weight: bold; font-size: {font_size}pt;")
        heater_hbox.addWidget(self.heater_btn)
        status_hbox.addLayout(heater_hbox)

        field_layout.addLayout(status_hbox)

        field_group.setLayout(field_layout)
        layout.addWidget(field_group)

        # New: Ramp control buttons section
        control_group = QGroupBox("Ramp Control")
        control_layout = QHBoxLayout()

        # TO SET button - Ramp to target field
        self.to_set_btn = QPushButton("TO SET")
        self.to_set_btn.clicked.connect(self.ramp_to_set)
        self.to_set_btn.setEnabled(False)
        self.to_set_btn.setMinimumWidth(80)
        self.to_set_btn.setStyleSheet("font-weight: bold;")
        control_layout.addWidget(self.to_set_btn)

        # TO ZERO button - Ramp to zero field
        self.to_zero_btn = QPushButton("TO ZERO")
        self.to_zero_btn.clicked.connect(self.ramp_to_zero)
        self.to_zero_btn.setEnabled(False)
        self.to_zero_btn.setMinimumWidth(80)
        self.to_zero_btn.setStyleSheet("font-weight: bold;")
        control_layout.addWidget(self.to_zero_btn)

        # HOLD button - Hold current field
        self.hold_btn = QPushButton("HOLD")
        self.hold_btn.clicked.connect(self.ramp_hold)
        self.hold_btn.setEnabled(False)
        self.hold_btn.setMinimumWidth(80)
        self.hold_btn.setStyleSheet("font-weight: bold;")
        control_layout.addWidget(self.hold_btn)

        control_group.setLayout(control_layout)
        layout.addWidget(control_group)

        self.setLayout(layout)

    def toggle_connection(self):
        """Toggle connection to MIPS instrument"""
        if self.connect_btn.text() == "Connect":
            self.connect_mips()
        else:
            self.disconnect_mips()

    def connect_mips(self):
        """Connect to MIPS instrument and start reading thread"""
        str_input = self.addr_input.text()
        try:
            from demag_gui.driver.virtual_instruments import OxfordMercuryiPS
            self.mips_instrument = OxfordMercuryiPS('mips', str_input)

            # Enable control elements
            self.target_sv_input.setEnabled(True)
            self.rate_sv_input.setEnabled(True)
            self.set_target_btn.setEnabled(True)
            self.set_rate_btn.setEnabled(True)
            self.heater_btn.setEnabled(True)
            self.to_set_btn.setEnabled(True)
            self.to_zero_btn.setEnabled(True)
            self.hold_btn.setEnabled(True)

            # Get initial values
            try:
                initial_target = self.mips_instrument.GRPZ.field_target()
                initial_rate = self.mips_instrument.GRPZ.field_ramp_rate() * 60
                self.target_sv_input.setText(f"{initial_target:.3f}")
                self.rate_sv_input.setText(f"{initial_rate:.3f}")
            except:
                pass  # Use defaults if reading fails

            # Start reading thread
            self.mips_thread = MIPSReadingThread(self.mips_instrument)
            self.mips_thread.mips_reading_ready.connect(self.update_readings)
            self.mips_thread.mips_reading_error.connect(self.handle_reading_error)
            self.mips_thread.start()

            # Update UI state
            self.connect_btn.setText("Disconnect")
            self.status_label.setText("Running")
            self.status_label.setStyleSheet("color: green")

        except Exception as e:
            QMessageBox.critical(self, "Connection Failed", f"Failed to connect to MIPS: {str(e)}")
            self.status_label.setText("Failed")
            self.status_label.setStyleSheet("color: red")

    def disconnect_mips(self):
        """Disconnect from MIPS instrument and stop reading thread"""
        try:
            # Stop reading thread
            if self.mips_thread:
                self.mips_thread.stop()
                self.mips_thread = None

            # Close instrument connection
            if self.mips_instrument:
                self.mips_instrument.close()
                self.mips_instrument = None

            # Disable all control elements
            self.target_sv_input.setEnabled(False)
            self.rate_sv_input.setEnabled(False)
            self.set_target_btn.setEnabled(False)
            self.set_rate_btn.setEnabled(False)
            self.heater_btn.setEnabled(False)
            self.to_set_btn.setEnabled(False)
            self.to_zero_btn.setEnabled(False)
            self.hold_btn.setEnabled(False)

            # Update UI state
            self.connect_btn.setText("Connect")
            self.status_label.setText("Disconnected")
            self.status_label.setStyleSheet("color: gray")

        except Exception as e:
            QMessageBox.critical(self, "Disconnect Failed", f"Failed to disconnect from MIPS: {str(e)}")

    def set_field_target(self):
        """Set target field value to instrument"""
        if not self.mips_instrument:
            return

        try:
            target_value = float(self.target_sv_input.text())
            self.mips_instrument.GRPZ.field_target(target_value)

            # Update CV display
            updated_target = self.mips_instrument.GRPZ.field_target()
            self.target_cv_display.setText(f"{updated_target}")

        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid number for target field")
        except Exception as e:
            QMessageBox.warning(self, "Set Error", f"Failed to set target field: {str(e)}")

    def set_field_rate(self):
        """Set field ramp rate to instrument"""
        if not self.mips_instrument:
            return

        try:
            rate_value = float(self.rate_sv_input.text())
            self.mips_instrument.GRPZ.field_ramp_rate(rate_value / 60)

            # Update CV display
            updated_rate = self.mips_instrument.GRPZ.field_ramp_rate() * 60
            self.rate_cv_display.setText(f"{updated_rate}")

        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid number for field rate")
        except Exception as e:
            QMessageBox.warning(self, "Set Error", f"Failed to set field rate: {str(e)}")

    def toggle_heater(self):
        """Toggle heater switch (placeholder function)"""
        pass

    def ramp_to_set(self):
        """Set ramp status to TO SET (ramp to target field)"""
        if not self.mips_instrument:
            return

        try:
            self.mips_instrument.GRPZ.ramp_status('TO SET')
            QMessageBox.information(self, "Success", "Ramp status set to TO SET")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to set ramp status: {str(e)}")

    def ramp_to_zero(self):
        """Set ramp status to TO ZERO (ramp to zero field)"""
        if not self.mips_instrument:
            return

        try:
            self.mips_instrument.GRPZ.ramp_status('TO ZERO')
            QMessageBox.information(self, "Success", "Ramp status set to TO ZERO")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to set ramp status: {str(e)}")

    def ramp_hold(self):
        """Set ramp status to HOLD (hold current field)"""
        if not self.mips_instrument:
            return

        try:
            self.mips_instrument.GRPZ.ramp_status('TO HOLD')
            QMessageBox.information(self, "Success", "Ramp status set to HOLD")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to set ramp status: {str(e)}")

    def update_readings(self, field_persistent, field_output, ramp_status, heater_switch,
                        field_target_cv, field_rate_cv):
        """Update UI with new instrument readings"""
        # Update field displays
        self.bpersistent_display.setText(f"{field_persistent}")
        self.bout_display.setText(f"{field_output}")

        # Update CV displays
        self.target_cv_display.setText(f"{field_target_cv}")
        self.rate_cv_display.setText(f"{field_rate_cv}")

        # Update status displays
        self.ramp_display.setText(ramp_status)
        self.heater_btn.setText(heater_switch.upper())

        # Set colors based on status
        font_size = self.font().pointSize()

        # Ramp status color coding
        if ramp_status.lower() == "ramping":
            self.ramp_display.setStyleSheet(f"font-weight: bold; color: orange; font-size: {font_size}pt;")
        elif ramp_status.lower() == "hold":
            self.ramp_display.setStyleSheet(f"font-weight: bold; color: green; font-size: {font_size}pt;")
        else:
            self.ramp_display.setStyleSheet(f"font-weight: bold; color: black; font-size: {font_size}pt;")

        # Heater button color coding
        if heater_switch.lower() == "on":
            self.heater_btn.setStyleSheet(f"font-weight: bold; color: red; font-size: {font_size}pt;")
        elif heater_switch.lower() == "off":
            self.heater_btn.setStyleSheet(f"font-weight: bold; color: green; font-size: {font_size}pt;")
        else:
            self.heater_btn.setStyleSheet(f"font-weight: bold; color: black; font-size: {font_size}pt;")

    def handle_reading_error(self, error_msg):
        """Handle reading thread errors"""
        QMessageBox.warning(self, "MIPS Reading Error", f"Error reading MIPS values: {error_msg}")

    def close(self):
        """Clean up when closing panel"""
        if self.mips_thread:
            self.mips_thread.stop()