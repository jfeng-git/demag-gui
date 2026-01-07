# nmr_control.py
from PyQt5.QtWidgets import *
from PyQt5.QtCore import QThread, pyqtSignal

class NMRReadingThread(QThread):
    reading_ready = pyqtSignal(float, float)  # M0, T (mK)
    reading_error = pyqtSignal(str)
    known_values_ready = pyqtSignal(float, float)  # Known M0, Known T
    known_values_error = pyqtSignal(str)
    
    def __init__(self, nmr_instrument, operation_type="read"):
        super().__init__()
        self.nmr = nmr_instrument
        self.operation_type = operation_type  # "read", "measure", "get_known", "set_known"
        self.known_m0 = None
        self.known_t = None
        self._is_running = True
    
    def set_operation_type(self, op_type):
        self.operation_type = op_type
    
    def set_known_values(self, m0, t):
        self.known_m0 = m0
        self.known_t = t
    
    def run(self):
        while self._is_running:
            try:
                if self.operation_type == "read":
                    m0 = self.nmr.M0()
                    t = self.nmr.TmK()
                    self.reading_ready.emit(m0, t)
                    
                elif self.operation_type == "measure":
                    self.nmr.OperationState('Single')
                    self.msleep(500)
                    m0 = self.nmr.M0()
                    t = self.nmr.TmK()
                    self.reading_ready.emit(m0, t)
                    
                elif self.operation_type == "get_known":
                    known_m0 = self.nmr.KnownM0_A()
                    known_t = self.nmr.KnownT_A()
                    self.known_values_ready.emit(known_m0, known_t)
                    
                elif self.operation_type == "set_known":
                    if self.known_m0 is not None:
                        # Set known M0
                        self.nmr.set_KnownM0_A(self.known_m0)
                    if self.known_t is not None:
                        # Set known T
                        self.nmr.set_KnownT_A(self.known_t)
                    self.known_values_ready.emit(self.known_m0, self.known_t)
                        
            except Exception as e:
                if self.operation_type in ["read", "measure"]:
                    self.reading_error.emit(str(e))
                else:
                    self.known_values_error.emit(str(e))
    
    def stop(self):
        self._is_running = False
        self.wait()

class NMRControlPanel(QGroupBox):
    def __init__(self):
        super().__init__("NMR")
        self.nmr_instrument = None
        self.nmr_thread = None
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Connection row
        conn_hbox = QHBoxLayout()
        self.addr_input = QLineEdit("GPIB1::22::INSTR")
        self.connect_btn = QPushButton("Connect")
        self.status_label = QLabel("Disconnected")
        self.status_label.setStyleSheet("color: gray")
        
        self.connect_btn.clicked.connect(self.toggle_connection)
        
        conn_hbox.addWidget(self.addr_input)
        conn_hbox.addWidget(self.connect_btn)
        conn_hbox.addWidget(self.status_label)
        layout.addLayout(conn_hbox)
        
        # Measurements section - ALL IN ONE LINE
        measurements_group = QGroupBox("Measurements")
        measurements_layout = QHBoxLayout()
        
        # M0 display
        m0_hbox = QHBoxLayout()
        m0_hbox.addWidget(QLabel("M0:"))
        self.m0_display = QLineEdit("Unknown")
        self.m0_display.setReadOnly(True)
        self.m0_display.setMinimumWidth(100)
        font_size = self.font().pointSize()
        self.m0_display.setStyleSheet(f"font-weight: bold; color: blue; font-size: {font_size}pt;")
        m0_hbox.addWidget(self.m0_display)
        measurements_layout.addLayout(m0_hbox)
        
        # Temperature display
        temp_hbox = QHBoxLayout()
        temp_hbox.addWidget(QLabel("T (mK):"))
        self.temp_display = QLineEdit("Unknown")
        self.temp_display.setReadOnly(True)
        self.temp_display.setMinimumWidth(100)
        self.temp_display.setStyleSheet(f"font-weight: bold; color: blue; font-size: {font_size}pt;")
        temp_hbox.addWidget(self.temp_display)
        measurements_layout.addLayout(temp_hbox)
        
        # Read button
        self.read_btn = QPushButton("Read")
        self.read_btn.clicked.connect(self.read_values)
        self.read_btn.setEnabled(False)
        measurements_layout.addWidget(self.read_btn)
        
        # Measure button
        self.measure_btn = QPushButton("Measure")
        self.measure_btn.clicked.connect(self.measure_values)
        self.measure_btn.setEnabled(False)
        measurements_layout.addWidget(self.measure_btn)
        
        measurements_layout.addStretch()
        measurements_group.setLayout(measurements_layout)
        layout.addWidget(measurements_group)
        
        # Known values section - ALL IN ONE LINE
        known_group = QGroupBox("Known Values")
        known_layout = QHBoxLayout()  # Changed to HBoxLayout
        
        # Known M0
        known_m0_hbox = QHBoxLayout()
        known_m0_hbox.addWidget(QLabel("Known M0:"))
        self.known_m0_input = QLineEdit("Unknown")  # Editable input field
        self.known_m0_input.setMinimumWidth(100)
        self.known_m0_input.setStyleSheet(f"font-size: {font_size}pt;")
        self.known_m0_input.setEnabled(False)  # Initially disabled
        known_m0_hbox.addWidget(self.known_m0_input)
        
        self.get_m0_btn = QPushButton("Get")
        self.get_m0_btn.clicked.connect(self.get_known_m0)
        self.get_m0_btn.setEnabled(False)
        known_m0_hbox.addWidget(self.get_m0_btn)
        
        self.set_m0_btn = QPushButton("Set")
        self.set_m0_btn.clicked.connect(self.set_known_m0)
        self.set_m0_btn.setEnabled(False)
        known_m0_hbox.addWidget(self.set_m0_btn)
        
        known_layout.addLayout(known_m0_hbox)
        
        # Known T
        known_t_hbox = QHBoxLayout()
        known_t_hbox.addWidget(QLabel("Known T (mK):"))
        self.known_t_input = QLineEdit("Unknown")  # Editable input field
        self.known_t_input.setMinimumWidth(100)
        self.known_t_input.setStyleSheet(f"font-size: {font_size}pt;")
        self.known_t_input.setEnabled(False)  # Initially disabled
        known_t_hbox.addWidget(self.known_t_input)
        
        self.get_t_btn = QPushButton("Get")
        self.get_t_btn.clicked.connect(self.get_known_t)
        self.get_t_btn.setEnabled(False)
        known_t_hbox.addWidget(self.get_t_btn)
        
        self.set_t_btn = QPushButton("Set")
        self.set_t_btn.clicked.connect(self.set_known_t)
        self.set_t_btn.setEnabled(False)
        known_t_hbox.addWidget(self.set_t_btn)
        
        known_layout.addLayout(known_t_hbox)
        
        known_layout.addStretch()
        known_group.setLayout(known_layout)
        layout.addWidget(known_group)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def toggle_connection(self):
        if self.connect_btn.text() == "Connect":
            self.connect_nmr()
        else:
            self.disconnect_nmr()
    
    def connect_nmr(self):
        str_input = self.addr_input.text()
        try:
            from driver.NMR import NMR
            self.nmr_instrument = NMR('nmr', str_input)
            
            # Enable buttons and input fields after successful connection
            self.read_btn.setEnabled(True)
            self.measure_btn.setEnabled(True)
            self.known_m0_input.setEnabled(True)
            self.known_t_input.setEnabled(True)
            self.get_m0_btn.setEnabled(True)
            self.set_m0_btn.setEnabled(True)
            self.get_t_btn.setEnabled(True)
            self.set_t_btn.setEnabled(True)
            
            self.connect_btn.setText("Disconnect")
            self.status_label.setText("Running")
            self.status_label.setStyleSheet("color: green")
            
        except Exception as e:
            QMessageBox.critical(self, "Connection Failed", f"Failed to connect to NMR: {str(e)}")
            self.status_label.setText("Failed")
            self.status_label.setStyleSheet("color: red")
    
    def disconnect_nmr(self):
        try:
            if self.nmr_thread:
                self.nmr_thread.stop()
                self.nmr_thread = None
            
            if self.nmr_instrument:
                self.nmr_instrument.close()
                self.nmr_instrument = None
            
            # Disable buttons and input fields
            self.read_btn.setEnabled(False)
            self.measure_btn.setEnabled(False)
            self.known_m0_input.setEnabled(False)
            self.known_t_input.setEnabled(False)
            self.get_m0_btn.setEnabled(False)
            self.set_m0_btn.setEnabled(False)
            self.get_t_btn.setEnabled(False)
            self.set_t_btn.setEnabled(False)

            
            self.connect_btn.setText("Connect")
            self.status_label.setText("Disconnected")
            self.status_label.setStyleSheet("color: gray")
            
        except Exception as e:
            QMessageBox.critical(self, "Disconnect Failed", f"Failed to disconnect from NMR: {str(e)}")
    
    def read_values(self):
        if not self.nmr_instrument:
            return
        
        self.nmr_thread = NMRReadingThread(self.nmr_instrument, "read")
        self.nmr_thread.reading_ready.connect(self.update_readings)
        self.nmr_thread.reading_error.connect(self.handle_reading_error)
        self.nmr_thread.start()
    
    def measure_values(self):
        if not self.nmr_instrument:
            return
        
        self.nmr_thread = NMRReadingThread(self.nmr_instrument, "measure")
        self.nmr_thread.reading_ready.connect(self.update_readings)
        self.nmr_thread.reading_error.connect(self.handle_reading_error)
        self.nmr_thread.start()
    
    def get_known_m0(self):
        if not self.nmr_instrument:
            return
        
        self.nmr_thread = NMRReadingThread(self.nmr_instrument, "get_known")
        self.nmr_thread.known_values_ready.connect(self.update_known_m0)
        self.nmr_thread.known_values_error.connect(self.handle_known_values_error)
        self.nmr_thread.start()
    
    def set_known_m0(self):
        if not self.nmr_instrument:
            return
        
        try:
            m0_value = float(self.known_m0_input.text())
            self.nmr_thread = NMRReadingThread(self.nmr_instrument, "set_known")
            self.nmr_thread.set_known_values(m0_value, None)  # Only set M0
            self.nmr_thread.known_values_ready.connect(self.update_known_m0)
            self.nmr_thread.known_values_error.connect(self.handle_known_values_error)
            self.nmr_thread.start()
            
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid number for M0")
    
    def get_known_t(self):
        if not self.nmr_instrument:
            return
        
        self.nmr_thread = NMRReadingThread(self.nmr_instrument, "get_known")
        self.nmr_thread.known_values_ready.connect(self.update_known_t)
        self.nmr_thread.known_values_error.connect(self.handle_known_values_error)
        self.nmr_thread.start()
    
    def set_known_t(self):
        if not self.nmr_instrument:
            return
        
        try:
            t_value = float(self.known_t_input.text())
            self.nmr_thread = NMRReadingThread(self.nmr_instrument, "set_known")
            self.nmr_thread.set_known_values(None, t_value)  # Only set T
            self.nmr_thread.known_values_ready.connect(self.update_known_t)
            self.nmr_thread.known_values_error.connect(self.handle_known_values_error)
            self.nmr_thread.start()
            
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid number for T")
    
    def update_readings(self, m0, t):
        self.m0_display.setText(f"{m0:.3f}")
        self.temp_display.setText(f"{t:.2f}")
        
        if self.nmr_thread:
            self.nmr_thread.stop()
            self.nmr_thread = None
    
    def update_known_m0(self, known_m0, known_t):
        # Update only M0 if value is provided
        if known_m0 is not None:
            self.known_m0_input.setText(f"{known_m0:.3f}")
        
        if self.nmr_thread:
            self.nmr_thread.stop()
            self.nmr_thread = None
    
    def update_known_t(self, known_m0, known_t):
        # Update only T if value is provided
        if known_t is not None:
            self.known_t_input.setText(f"{known_t:.2f}")
        
        if self.nmr_thread:
            self.nmr_thread.stop()
            self.nmr_thread = None
    
    def handle_reading_error(self, error_msg):
        QMessageBox.warning(self, "NMR Reading Error", f"Error reading NMR values: {error_msg}")
        self.m0_display.setText("Error")
        self.temp_display.setText("Error")
        
        if self.nmr_thread:
            self.nmr_thread.stop()
            self.nmr_thread = None
    
    def handle_known_values_error(self, error_msg):
        QMessageBox.warning(self, "NMR Known Values Error", f"Error handling known values: {error_msg}")
        
        if self.nmr_thread:
            self.nmr_thread.stop()
            self.nmr_thread = None
    
    def close(self):
        if self.nmr_thread:
            self.nmr_thread.stop()