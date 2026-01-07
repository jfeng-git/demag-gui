# mips_control.py (修改heater switch和添加检查)
from PyQt5.QtWidgets import *
from PyQt5.QtCore import QThread, pyqtSignal

class MIPSReadingThread(QThread):
    mips_reading_ready = pyqtSignal(float, float, str, str, float, float)
    mips_reading_error = pyqtSignal(str)
    
    def __init__(self, mips_instrument):
        super().__init__()
        self.mips = mips_instrument
        self._is_running = True
    
    def run(self):
        while self._is_running:
            try:
                field_persistent = self.mips.GRPZ.field_persistent()
                field_output = self.mips.GRPZ.field()
                ramp_status = self.mips.GRPZ.ramp_status()
                heater_switch = self.mips.GRPZ.heater_switch()
                field_target_cv = self.mips.GRPZ.field_target()
                field_rate_cv = self.mips.GRPZ.field_ramp_rate() * 60
                
                self.mips_reading_ready.emit(
                    field_persistent, field_output, ramp_status, heater_switch, 
                    field_target_cv, field_rate_cv
                )
                self.msleep(1000)
            except Exception as e:
                self.mips_reading_error.emit(str(e))
                break
    
    def stop(self):
        self._is_running = False
        self.wait()

class MIPSControlPanel(QGroupBox):
    def __init__(self):
        super().__init__("MIPS")
        self.mips_instrument = None
        self.mips_thread = None
        
        self.setup_ui()
    
    def setup_ui(self):
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
        
        # Field displays: Bpersistent and Bout
        field_display_hbox = QHBoxLayout()
        
        # Bpersistent
        bpersistent_hbox = QHBoxLayout()
        bpersistent_hbox.addWidget(QLabel("Bpersistent (T):"))
        self.bpersistent_display = QLineEdit("Unknown")
        self.bpersistent_display.setReadOnly(True)
        self.bpersistent_display.setMinimumWidth(120)
        font_size = self.font().pointSize()
        self.bpersistent_display.setStyleSheet(f"font-weight: bold; color: blue; font-size: {font_size}pt;")
        bpersistent_hbox.addWidget(self.bpersistent_display)
        field_display_hbox.addLayout(bpersistent_hbox)
        
        field_display_hbox.addSpacing(20)
        
        # Bout
        bout_hbox = QHBoxLayout()
        bout_hbox.addWidget(QLabel("Bout (T):"))
        self.bout_display = QLineEdit("Unknown")
        self.bout_display.setReadOnly(True)
        self.bout_display.setMinimumWidth(120)
        self.bout_display.setStyleSheet(f"font-weight: bold; color: green; font-size: {font_size}pt;")
        bout_hbox.addWidget(self.bout_display)
        field_display_hbox.addLayout(bout_hbox)
        
        field_display_hbox.addStretch()
        field_layout.addLayout(field_display_hbox)
        
        # Target field: CV and SV
        target_hbox = QHBoxLayout()
        
        # Target CV
        target_cv_hbox = QHBoxLayout()
        target_cv_hbox.addWidget(QLabel("Target CV (T):"))
        self.target_cv_display = QLineEdit("Unknown")
        self.target_cv_display.setReadOnly(True)
        self.target_cv_display.setMinimumWidth(100)
        self.target_cv_display.setStyleSheet(f"font-size: {font_size}pt;")
        target_cv_hbox.addWidget(self.target_cv_display)
        target_hbox.addLayout(target_cv_hbox)
        
        target_hbox.addSpacing(20)
        
        # Target SV
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
        target_hbox.addStretch()
        field_layout.addLayout(target_hbox)
        
        # Rate: CV and SV
        rate_hbox = QHBoxLayout()
        
        # Rate CV
        rate_cv_hbox = QHBoxLayout()
        rate_cv_hbox.addWidget(QLabel("Rate CV (T/min):"))
        self.rate_cv_display = QLineEdit("Unknown")
        self.rate_cv_display.setReadOnly(True)
        self.rate_cv_display.setMinimumWidth(100)
        self.rate_cv_display.setStyleSheet(f"font-size: {font_size}pt;")
        rate_cv_hbox.addWidget(self.rate_cv_display)
        rate_hbox.addLayout(rate_cv_hbox)
        
        rate_hbox.addSpacing(20)
        
        # Rate SV
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
        rate_hbox.addStretch()
        field_layout.addLayout(rate_hbox)
        
        # Ramp status and heater switch
        status_hbox = QHBoxLayout()
        
        # Ramp status
        ramp_hbox = QHBoxLayout()
        ramp_hbox.addWidget(QLabel("Ramp Status:"))
        self.ramp_display = QLineEdit("Unknown")
        self.ramp_display.setReadOnly(True)
        self.ramp_display.setMinimumWidth(150)
        self.ramp_display.setStyleSheet(f"font-weight: bold; font-size: {font_size}pt;")
        ramp_hbox.addWidget(self.ramp_display)
        status_hbox.addLayout(ramp_hbox)
        
        status_hbox.addSpacing(20)
        
        # Heater switch - changed to button
        heater_hbox = QHBoxLayout()
        heater_hbox.addWidget(QLabel("Heater Switch:"))
        self.heater_btn = QPushButton("Unknown")
        self.heater_btn.clicked.connect(self.toggle_heater)
        self.heater_btn.setEnabled(False)
        self.heater_btn.setMinimumWidth(150)
        self.heater_btn.setStyleSheet(f"font-weight: bold; font-size: {font_size}pt;")
        heater_hbox.addWidget(self.heater_btn)
        status_hbox.addLayout(heater_hbox)
        
        status_hbox.addStretch()
        field_layout.addLayout(status_hbox)
        
        field_group.setLayout(field_layout)
        layout.addWidget(field_group)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def toggle_connection(self):
        if self.connect_btn.text() == "Connect":
            self.connect_mips()
        else:
            self.disconnect_mips()
    
    def connect_mips(self):
        str_input = self.addr_input.text()
        try:
            from qcodes.instrument_drivers.oxford import OxfordMercuryiPS
            self.mips_instrument = OxfordMercuryiPS('mips', str_input)
            
            self.target_sv_input.setEnabled(True)
            self.rate_sv_input.setEnabled(True)
            self.set_target_btn.setEnabled(True)
            self.set_rate_btn.setEnabled(True)
            self.heater_btn.setEnabled(True)
            
            try:
                initial_target = self.mips_instrument.GRPZ.field_target()
                initial_rate = self.mips_instrument.GRPZ.field_ramp_rate() * 60
                self.target_sv_input.setText(f"{initial_target:.3f}")
                self.rate_sv_input.setText(f"{initial_rate:.3f}")
            except:
                pass
            
            self.mips_thread = MIPSReadingThread(self.mips_instrument)
            self.mips_thread.mips_reading_ready.connect(self.update_readings)
            self.mips_thread.mips_reading_error.connect(self.handle_reading_error)
            self.mips_thread.start()
            
            self.connect_btn.setText("Disconnect")
            self.status_label.setText("Running")
            self.status_label.setStyleSheet("color: green")
            
        except Exception as e:
            QMessageBox.critical(self, "Connection Failed", f"Failed to connect to MIPS: {str(e)}")
            self.status_label.setText("Failed")
            self.status_label.setStyleSheet("color: red")
    
    def disconnect_mips(self):
        try:
            if self.mips_thread:
                self.mips_thread.stop()
                self.mips_thread = None
            
            if self.mips_instrument:
                self.mips_instrument.close()
                self.mips_instrument = None
            
            self.target_sv_input.setEnabled(False)
            self.rate_sv_input.setEnabled(False)
            self.set_target_btn.setEnabled(False)
            self.set_rate_btn.setEnabled(False)
            self.heater_btn.setEnabled(False)
            
            self.connect_btn.setText("Connect")
            self.status_label.setText("Disconnected")
            self.status_label.setStyleSheet("color: gray")
            
        except Exception as e:
            QMessageBox.critical(self, "Disconnect Failed", f"Failed to disconnect from MIPS: {str(e)}")
    
    def set_field_target(self):
        if not self.mips_instrument:
            return
        
        try:
            target_value = float(self.target_sv_input.text())
            self.mips_instrument.GRPZ.field_target(target_value)
            
            updated_target = self.mips_instrument.GRPZ.field_target()
            self.target_cv_display.setText(f"{updated_target:.3f}")
            
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid number for target field")
        except Exception as e:
            QMessageBox.warning(self, "Set Error", f"Failed to set target field: {str(e)}")
    
    def set_field_rate(self):
        if not self.mips_instrument:
            return
        
        try:
            rate_value = float(self.rate_sv_input.text())
            self.mips_instrument.GRPZ.field_ramp_rate(rate_value / 60)
            
            updated_rate = self.mips_instrument.GRPZ.field_ramp_rate() * 60
            self.rate_cv_display.setText(f"{updated_rate:.3f}")
            
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid number for field rate")
        except Exception as e:
            QMessageBox.warning(self, "Set Error", f"Failed to set field rate: {str(e)}")
    
    def toggle_heater(self):
        """Toggle heater switch with safety check"""
        if not self.mips_instrument:
            return
        
        # Check Bout vs Bpersistent difference
        try:
            # Get current values from displays
            bout_text = self.bout_display.text()
            bpersistent_text = self.bpersistent_display.text()
            
            if bout_text != "Unknown" and bpersistent_text != "Unknown":
                bout = float(bout_text)
                bpersistent = float(bpersistent_text)  
                
                # Check if field is not persistent
                print(bout)
                print(bpersistent)
                if abs(bout - bpersistent) > 0.0001:
                    QMessageBox.warning(
                        self, 
                        "Heater Switch Error", 
                        f"Cannot switch heater: Field not persistent\n"
                        f"Bout={bout:.4f}T, Bpersistent={bpersistent:.4f}T\n"
                        f"Difference={abs(bout-bpersistent):.6f}T > 0.0001T"
                    )
                    return
        except Exception as e:
            QMessageBox.warning(self, "Check Error", f"Cannot verify field persistence: {str(e)}")
            return
        
        # Toggle heater state
        try:
            current_state = self.heater_btn.text().lower()
            # if current_state == "off":
            #     # Turn heater ON
            #     self.mips_instrument.GRPZ.heater_switch('on')
            #     self.heater_btn.setText("ON")
            #     self.heater_btn.setStyleSheet(f"font-weight: bold; color: red; font-size: {self.font().pointSize()}pt;")
            # else:
            #     # Turn heater OFF
            #     self.mips_instrument.GRPZ.heater_switch('off')
            #     self.heater_btn.setText("OFF")
            #     self.heater_btn.setStyleSheet(f"font-weight: bold; color: green; font-size: {self.font().pointSize()}pt;")
                
        except Exception as e:
            QMessageBox.warning(self, "Heater Error", f"Failed to toggle heater: {str(e)}")
    
    def update_readings(self, field_persistent, field_output, ramp_status, heater_switch, 
                        field_target_cv, field_rate_cv):
        # Update field displays
        self.bpersistent_display.setText(f"{field_persistent:.3f}")
        self.bout_display.setText(f"{field_output:.3f}")
        
        # Update CV displays
        self.target_cv_display.setText(f"{field_target_cv:.3f}")
        self.rate_cv_display.setText(f"{field_rate_cv:.3f}")
        
        # Update status displays
        self.ramp_display.setText(ramp_status)
        self.heater_btn.setText(heater_switch.upper())
        
        # Set colors based on status
        font_size = self.font().pointSize()
        
        # Ramp status color
        if ramp_status.lower() == "ramping":
            self.ramp_display.setStyleSheet(f"font-weight: bold; color: orange; font-size: {font_size}pt;")
        elif ramp_status.lower() == "holding":
            self.ramp_display.setStyleSheet(f"font-weight: bold; color: green; font-size: {font_size}pt;")
        else:
            self.ramp_display.setStyleSheet(f"font-weight: bold; color: black; font-size: {font_size}pt;")
        
        # Heater button color
        if heater_switch.lower() == "on":
            self.heater_btn.setStyleSheet(f"font-weight: bold; color: red; font-size: {font_size}pt;")
        elif heater_switch.lower() == "off":
            self.heater_btn.setStyleSheet(f"font-weight: bold; color: green; font-size: {font_size}pt;")
        else:
            self.heater_btn.setStyleSheet(f"font-weight: bold; color: black; font-size: {font_size}pt;")
    
    def handle_reading_error(self, error_msg):
        QMessageBox.warning(self, "MIPS Reading Error", f"Error reading MIPS values: {error_msg}")
        self.bpersistent_display.setText("Error")
        self.bout_display.setText("Error")
        self.target_cv_display.setText("Error")
        self.rate_cv_display.setText("Error")
    
    def close(self):
        if self.mips_thread:
            self.mips_thread.stop()