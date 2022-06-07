import sys
from glob import glob

from PyQt6.QtGui import QFontDatabase
from PyQt6.QtWidgets import QApplication

from gui import MainWindow

app = QApplication(sys.argv)

for font in glob("fonts/*.?tf"):
    QFontDatabase.addApplicationFont(font)
    
app.setStyleSheet("QWidget{font-size: 12px;}")


window = MainWindow()
window.show()

sys.exit(app.exec())
