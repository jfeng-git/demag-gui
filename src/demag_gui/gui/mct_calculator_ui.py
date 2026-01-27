# mct_calculator_ui.py
import sys
from demag_gui.utils.DemagCalculator import MctCalculator

from PyQt5.QtWidgets import *

# mct_calculator_ui.py
class MCTCalculatorUI(QWidget):
    def __init__(self, mct_calc):
        super().__init__()
        self.mct_calc = mct_calc
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(2)

        main_layout.addWidget(QLabel("Temperature Calculation", styleSheet="font-weight: bold;"))
        main_layout.addLayout(self.create_temperature_layout())

        main_layout.addWidget(QLabel("Recalibration", styleSheet="font-weight: bold;"))
        main_layout.addLayout(self.create_recalibration_layout())

        self.setLayout(main_layout)

    def create_temperature_layout(self):
        layout = QVBoxLayout()

        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Capacitance C:"))
        self.c_input = QLineEdit("74.0")
        self.c_input.setMinimumWidth(120)
        input_layout.addWidget(self.c_input)
        input_layout.addStretch()

        self.calc_temp_btn = QPushButton("Calculate Temperature")
        self.calc_temp_btn.clicked.connect(self.calculate_temperature)
        input_layout.addWidget(self.calc_temp_btn)

        layout.addLayout(input_layout)

        self.temp_output = QLabel("")
        self.temp_output.setStyleSheet(f"font-weight: bold; color: red; font-size: {12}pt;")
        layout.addWidget(self.temp_output)

        return layout

    def create_recalibration_layout(self):
        layout = QVBoxLayout()
        layout.setSpacing(2)
        layout.addLayout(self.create_calibration_point_layout(1))
        layout.addLayout(self.create_calibration_point_layout(2))
        layout.addLayout(self.create_recalibration_buttons())

        self.cal_status = QLabel("")
        layout.addWidget(self.cal_status)

        return layout


    def create_calibration_point_layout(self, point_num):
        layout = QHBoxLayout()
        layout.addWidget(QLabel(f"Point {point_num}: C{point_num} ="))

        input_field = QLineEdit()
        input_field.setMaximumWidth(100)
        layout.addWidget(input_field)
        setattr(self, f"c{point_num}_input", input_field)

        layout.addWidget(QLabel(f"P{point_num} ="))

        dropdown = QComboBox()
        self.populate_p_dropdown(dropdown)
        dropdown.setCurrentIndex(-1)
        dropdown.setMaximumWidth(250)
        layout.addWidget(dropdown)
        setattr(self, f"p{point_num}_dropdown", dropdown)

        layout.addStretch()
        return layout

    def create_recalibration_buttons(self):
        layout = QHBoxLayout()

        self.recal_btn = QPushButton("Recalibrate with new points")
        self.recal_btn.clicked.connect(self.recalibrate_with_new_points)
        layout.addWidget(self.recal_btn)

        self.restore_btn = QPushButton("Restore Original")
        self.restore_btn.clicked.connect(self.restore_original)
        layout.addWidget(self.restore_btn)
        layout.addStretch()

        return layout

    def populate_p_dropdown(self, dropdown):
        dropdown.addItem(f"P_Astd, {self.mct_calc.P_Astd:.6f}", self.mct_calc.P_Astd)
        dropdown.addItem(f"P_ABstd, {self.mct_calc.P_ABstd:.6f}", self.mct_calc.P_ABstd)
        dropdown.addItem(f"P_Neel, {self.mct_calc.P_Neel:.6f}", self.mct_calc.P_Neel)
        dropdown.addItem(f"P_min, {self.mct_calc.P_min:.6f}", self.mct_calc.P_Neel)

    def calculate_temperature(self):
        try:
            c_value = float(self.c_input.text())
            t_low = self.mct_calc.C2T_low(c_value)
            t_high = self.mct_calc.C2T_high(c_value)
            p_value = self.mct_calc.C2P_low(c_value)

            output = f"C = {c_value} pF,\t"
            output += f"P = {p_value:.5f} MPa,\t"
            output += f"T_low = {t_low:.4f} mK,\t"
            output += f"T_high = {t_high:.4f} mK"

            self.temp_output.setText(output)
        except Exception as e:
            self.temp_output.setText(f"Error: {str(e)}")

    def recalibrate_from_pmin(self):
        try:
            c0 = float(self.c0_input.text())
            p0 = self.mct_calc.P_min
            new_points = [[c0, p0]]
            self.mct_calc.recalibrate(new_points)
            self.cal_status.setText(f"✓ Recalibrated from Pmin point: C={c0}, P={p0:.6f}")
        except Exception as e:
            self.cal_status.setText(f"✗ Error: {str(e)}")

    def recalibrate_with_new_points(self):
        new_points = []

        try:
            for i in [1, 2]:
                c_input = getattr(self, f"c{i}_input")
                p_dropdown = getattr(self, f"p{i}_dropdown")

                if c_input.text() and p_dropdown.currentIndex() >= 0:
                    c = float(c_input.text())
                    p = p_dropdown.currentData()
                    new_points.append([c, p])

            if new_points:
                self.mct_calc.recalibrate(new_points)
                self.cal_status.setText(f"✓ Recalibrated with {len(new_points)} point(s)")
            else:
                self.cal_status.setText("Please enter at least one calibration point")
        except Exception as e:
            self.cal_status.setText(f"✗ Error: {str(e)}")

    def restore_original(self):
        try:
            self.mct_calc.get_original_coes()
            self.cal_status.setText("✓ Restored to original coefficients")
        except Exception as e:
            self.cal_status.setText(f"✗ Error: {str(e)}")

