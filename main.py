from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QTabWidget
import sys
from Winding_tab import setup_main_tab, update_winding, save_stator_image, handle_single_layer_toggle
from Voltage_tab import setup_voltage_checker_tab
from MMF_Harmonics_tab import setup_koil_harmonics_tab

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Multi-Phase Winding Simulator")
        self.setMinimumSize(1200, 800)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.tab_main = QWidget()
        self.tabs.addTab(self.tab_main, "Winding Simulator")

        self.tab_voltage = QWidget()
        self.tabs.addTab(self.tab_voltage, "Voltage Checker")
        
        self.tab_koil_harmonics = QWidget()
        self.tabs.addTab(self.tab_koil_harmonics, "MMF and Harmonics")
        
        setup_main_tab(self)
        setup_voltage_checker_tab(self)
        setup_koil_harmonics_tab(self)
        
        self.update_winding()

    update_winding = update_winding
    save_stator_image = save_stator_image
    handle_single_layer_toggle = handle_single_layer_toggle

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.showMaximized()
    sys.exit(app.exec_())
