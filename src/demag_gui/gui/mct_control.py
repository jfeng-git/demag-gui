from PyQt5.QtWidgets import *
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QFont
import pyqtgraph as pg
import numpy as np
from datetime import datetime
from demag_gui.utils.DemagCalculator import MctCalculator

class MCTReadingThread(QThread):
    reading_ready = pyqtSignal(float, float, float, float)  # cap, loss, temp_low, timestamp
    reading_error = pyqtSignal(str)
    
    def __init__(self, mct_instrument, mct_calc):
        super().__init__()
        self.mct = mct_instrument
        self.mct_calc = mct_calc
        self._is_running = True
    
    def run(self):
        while self._is_running:
            try:
                cap_value = self.mct.C()
                loss_value = self.mct.L()
                t_low = self.mct_calc.C2T_low(cap_value)
                timestamp = datetime.now().timestamp()
                
                self.reading_ready.emit(cap_value, loss_value, t_low, timestamp)
                self.msleep(100)
            except Exception as e:
                self.reading_error.emit(str(e))
                break
    
    def stop(self):
        self._is_running = False
        self.wait()

class MCTControlPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.mct_calc = MctCalculator()
        self.mct_instrument = None
        self.mct_thread = None
        
        # Data storage
        self.cap_data = []
        self.temp_data = []
        self.time_data = []
        self.max_points = 1000
        self.graph_type = "capacitance"
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(0)

        # Control section
        layout.addWidget(self.create_control_section())
        
        # Graph section
        layout.addWidget(self.create_graph_section())
        
        # Calculator
        from demag_gui.gui.mct_calculator_ui import MCTCalculatorUI
        calculator_ui = MCTCalculatorUI(self.mct_calc)
        layout.addWidget(calculator_ui)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def create_control_section(self):
        group = QGroupBox("MCT Control")
        layout = QVBoxLayout()
        layout.setSpacing(0)
        
        # Connection row
        conn_hbox = QHBoxLayout()
        self.addr_input = QLineEdit("GPIB0::28::INSTR")
        self.connect_btn = QPushButton("Connect")
        self.status_label = QLabel("Disconnected")
        self.status_label.setStyleSheet("color: gray")
        
        self.connect_btn.clicked.connect(self.toggle_connection)
        
        conn_hbox.addWidget(self.addr_input)
        conn_hbox.addWidget(self.connect_btn)
        conn_hbox.addWidget(self.status_label)
        layout.addLayout(conn_hbox)
        
        # Readings display row
        readings_hbox = QHBoxLayout()
        
        # Capacitance
        cap_hbox = QHBoxLayout()
        cap_hbox.addWidget(QLabel("C_mct (pF):"))
        self.cap_display = QLineEdit("0")
        self.cap_display.setReadOnly(True)
        self.cap_display.setMinimumWidth(50)
        font_size = self.font().pointSize()
        self.cap_display.setStyleSheet(f"font-weight: bold; color: red; font-size: {font_size}pt;")
        cap_hbox.addWidget(self.cap_display)
        readings_hbox.addLayout(cap_hbox)
        
        readings_hbox.addSpacing(20)
        
        # Temperature
        temp_hbox = QHBoxLayout()
        temp_hbox.addWidget(QLabel("T_mct (mK):"))
        self.temp_display = QLineEdit("0")
        self.temp_display.setReadOnly(True)
        self.temp_display.setMinimumWidth(50)
        self.temp_display.setStyleSheet(f"font-weight: bold; color: red;")
        temp_hbox.addWidget(self.temp_display)
        readings_hbox.addLayout(temp_hbox)
        
        readings_hbox.addSpacing(20)
        
        # Loss
        loss_hbox = QHBoxLayout()
        loss_hbox.addWidget(QLabel("Loss (uS):"))
        self.loss_display = QLineEdit("0")
        self.loss_display.setReadOnly(True)
        self.loss_display.setMinimumWidth(50)
        self.loss_display.setStyleSheet(f"font-weight: bold; color: red; font-size: {font_size}pt;")
        loss_hbox.addWidget(self.loss_display)
        readings_hbox.addLayout(loss_hbox)
        
        readings_hbox.addStretch()
        layout.addLayout(readings_hbox)
        
        group.setLayout(layout)
        return group
    
    def create_graph_section(self):
        group = QGroupBox("Real-time Monitoring")
        layout = QVBoxLayout()
        layout.setSpacing(0)
        
        # Graph type selection
        graph_select_layout = QHBoxLayout()
        graph_select_layout.addWidget(QLabel("Graph Type:"))
        
        self.graph_type_combo = QComboBox()
        self.graph_type_combo.addItems(["Capacitance", "Temperature"])
        self.graph_type_combo.currentTextChanged.connect(self.change_graph_type)
        graph_select_layout.addWidget(self.graph_type_combo)
        
        graph_select_layout.addStretch()
        layout.addLayout(graph_select_layout)
        
        # Create graph widget
        self.graph_widget = pg.GraphicsLayoutWidget()
        self.graph_widget.setBackground('w')
        # self.graph_widget.setFixedHeight(600)
        layout.addWidget(self.graph_widget)

        # Create plot
        self.plot = self.graph_widget.addPlot(title="Real-time Monitoring")
        
        # Set axis colors to black
        self.plot.getAxis('left').setPen('k')
        self.plot.getAxis('bottom').setPen('k')
        
        # Set label colors to black
        self.plot.setLabel('left', 'Capacitance', units='F', color='k')
        self.plot.setLabel('bottom', 'Time', units='s', color='k')
        
        # Set title color to black
        self.plot.setTitle("Capacitance vs Time", color='k')
        
        # Show grid with gray color
        self.plot.showGrid(x=True, y=True, alpha=0.3)
        
        # Create curve with black line
        self.curve = self.plot.plot(pen=pg.mkPen('k', width=2))
        
        group.setLayout(layout)
        return group
    
    def toggle_connection(self):
        if self.connect_btn.text() == "Connect":
            self.connect_mct()
        else:
            self.disconnect_mct()
    
    def connect_mct(self):
        str_input = self.addr_input.text()
        try:
            # from demag_gui.driver.AH2500A import AH2500A
            from demag_gui.driver.virtual_instruments import AH2500A
            self.mct_instrument = AH2500A('mct', str_input)
            
            self.mct_thread = MCTReadingThread(self.mct_instrument, self.mct_calc)
            self.mct_thread.reading_ready.connect(self.update_readings)
            self.mct_thread.reading_error.connect(self.handle_reading_error)
            self.mct_thread.start()
            
            # Clear previous data
            self.cap_data.clear()
            self.temp_data.clear()
            self.time_data.clear()
            
            self.connect_btn.setText("Disconnect")
            self.status_label.setText("Running")
            self.status_label.setStyleSheet("color: green")
            
        except Exception as e:
            QMessageBox.critical(self, "Connection Failed", f"Failed to connect to MCT: {str(e)}")
            self.status_label.setText("Failed")
            self.status_label.setStyleSheet("color: red")
    
    def disconnect_mct(self):
        try:
            if self.mct_thread:
                self.mct_thread.stop()
                self.mct_thread = None
            
            if self.mct_instrument:
                self.mct_instrument.close()
                self.mct_instrument = None

            self.connect_btn.setText("Connect")
            self.status_label.setText("Disconnected")
            self.status_label.setStyleSheet("color: gray")
            
        except Exception as e:
            QMessageBox.critical(self, "Disconnect Failed", f"Failed to disconnect from MCT: {str(e)}")
    
    def update_readings(self, cap_value, loss_value, temp_low, timestamp):
        # Update display
        self.cap_display.setText(f"{cap_value:.6f}")
        self.loss_display.setText(f"{loss_value:.4f}")
        self.temp_display.setText(f"{temp_low:.4f}")
        # Store data
        self.cap_data.append(cap_value)
        self.temp_data.append(temp_low)
        self.time_data.append(timestamp)
        
        # Keep only recent data
        if len(self.cap_data) > self.max_points:
            self.cap_data.pop(0)
            self.temp_data.pop(0)
            self.time_data.pop(0)
        
        # Update plot
        self.update_plot()
    
    def handle_reading_error(self, error_msg):
        QMessageBox.warning(self, "MCT Reading Error", f"Error reading MCT values: {error_msg}")
        self.cap_display.setText("Error")
        self.temp_display.setText("Error")
        self.loss_display.setText("Error")
    
    def change_graph_type(self, graph_type):
        self.graph_type = graph_type.lower()
        
        if self.graph_type == "capacitance":
            self.plot.setLabel('left', 'Capacitance', units='F', color='k')
            self.plot.setTitle("Capacitance vs Time", color='k')
        else:  # temperature
            self.plot.setLabel('left', 'Temperature', units='mK', color='k')
            self.plot.setTitle("Temperature vs Time", color='k')
        
        self.update_plot()
    
    def update_plot(self):
        if not self.time_data:
            return
        
        x = np.array(self.time_data) - self.time_data[0]  # Relative time
        if self.graph_type == "capacitance":
            y = np.array(self.cap_data)
        else:  # temperature
            y = np.array(self.temp_data)
        
        self.curve.setData(x, y)
    
    def close(self):
        if self.mct_thread:
            self.mct_thread.stop()