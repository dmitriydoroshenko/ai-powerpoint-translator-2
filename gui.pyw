import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                             QWidget, QFileDialog, QLabel, QTextEdit)
from PyQt5.QtCore import QThread, pyqtSignal, Qt

try:
    from main import process_presentation
except ImportError:
    print("Ошибка: Не найден файл main.py")

class TranslationWorker(QThread):
    """Поток для выполнения перевода конкретного файла"""
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path

    def run(self):
        if not self.file_path:
            self.finished_signal.emit()
            return

        try:
            process_presentation(self.file_path, callback=self.log_signal.emit)
        except Exception as e:
            self.log_signal.emit(f"❌ Критическая ошибка: {str(e)}")

        self.finished_signal.emit()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.selected_file = "" 
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("AI PowerPoint Translator")
        self.setMinimumSize(500, 400)

        layout = QVBoxLayout()
        layout.setSpacing(15)

        self.info_label = QLabel("Выберите файл .pptx")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(self.info_label)

        self.btn_browse = QPushButton("📂 Выбрать файл")
        self.btn_browse.setMinimumHeight(40)
        self.btn_browse.clicked.connect(self.browse_file)
        layout.addWidget(self.btn_browse)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("Ожидание запуска...")
        layout.addWidget(self.log_output)

        self.btn_start = QPushButton("🚀 Начать перевод")
        self.btn_start.setEnabled(False)
        self.btn_start.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71; 
                color: white; 
                padding: 10px; 
                font-size: 14px; 
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        self.btn_start.clicked.connect(self.run_translation)
        layout.addWidget(self.btn_start)

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def browse_file(self):
        file, _ = QFileDialog.getOpenFileName(
            self, "Выберите презентацию", "", "PowerPoint Files (*.pptx)"
        )
        if file:
            self.selected_file = file
            self.btn_start.setEnabled(True)
            self.info_label.setText(f"Файл: {os.path.basename(file)}")
            # Убрали append лога при выборе

    def run_translation(self):
        self.btn_start.setEnabled(False)
        self.btn_browse.setEnabled(False)
        self.log_output.clear() # Очищаем экран перед новым запуском
        
        self.worker = TranslationWorker(self.selected_file)
        self.worker.log_signal.connect(self.update_log)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()

    def update_log(self, text):
        self.log_output.append(text)
        self.log_output.ensureCursorVisible()

    def on_finished(self):
        self.btn_start.setEnabled(True)
        self.btn_browse.setEnabled(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
