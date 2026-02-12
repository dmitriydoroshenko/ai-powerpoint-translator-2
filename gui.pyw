import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                             QWidget, QFileDialog, QLabel, QTextEdit, QInputDialog, 
                             QLineEdit, QMessageBox)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QSettings

try:
    from main import process_presentation
    from translator import set_api_key, validate_api_key
except ImportError as e:
    print(f"Ошибка импорта: {e}")

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
        self.settings = QSettings("AI_Tools", "PPT_Translator")
        self.selected_file = "" 
        self.init_ui()
        self.check_api_key()

    def check_api_key(self):
        """Проверяет ключ при старте. Если в реестре невалидный ключ — запрашивает новый."""
        api_key = self.settings.value("openai_api_key", "")
        
        while True:
            if api_key:
                is_valid, error_msg = validate_api_key(api_key)
                
                if is_valid:
                    set_api_key(api_key)
                    self.log_output.clear()
                    break
                else:
                    self.update_log(f"❌ Сохраненный ключ невалиден: {error_msg}")
                    api_key = ""
                    continue

            key, ok = QInputDialog.getText(
                self, "Настройка API", 
                "Введите ваш OpenAI API Key (ключ будет проверен и сохранен в реестре):", 
                QLineEdit.EchoMode.Password
            )
            
            if ok and key.strip():
                self.update_log("⏳ Тестирование нового ключа...")
                is_valid, error_msg = validate_api_key(key.strip())
                
                if is_valid:
                    self.settings.setValue("openai_api_key", key.strip())
                    api_key = key.strip()
                    set_api_key(api_key)
                    QMessageBox.information(self, "Успех", "API ключ успешно проверен и сохранен!")
                    self.log_output.clear()
                    break
                else:
                    QMessageBox.critical(self, "Ошибка", f"Ключ не прошел проверку, попробуйте другой ключ")
                    api_key = ""
            else:
                sys.exit(0)

    def init_ui(self):
        self.setWindowTitle("AI PowerPoint Translator")
        self.setMinimumSize(550, 500)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)

        self.info_label = QLabel("Выберите презентацию для перевода (.pptx)")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(self.info_label)

        self.btn_browse = QPushButton("📂 Выбрать файл")
        self.btn_browse.setMinimumHeight(45)
        self.btn_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_browse.clicked.connect(self.browse_file)
        layout.addWidget(self.btn_browse)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("Лог процесса перевода появится здесь...")
        layout.addWidget(self.log_output)

        self.btn_start = QPushButton("🚀 Начать перевод")
        self.btn_start.setEnabled(False)
        self.btn_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start.setStyleSheet("""
            QPushButton { 
                background-color: #2ecc71; 
                color: white; 
                padding: 12px; 
                font-size: 14px; 
                font-weight: bold; 
                border-radius: 6px; 
            }
            QPushButton:disabled { background-color: #95a5a6; }
            QPushButton:hover { background-color: #27ae60; }
        """)
        self.btn_start.clicked.connect(self.run_translation)
        layout.addWidget(self.btn_start)

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def browse_file(self):
        """Диалог выбора файла."""
        file, _ = QFileDialog.getOpenFileName(self, "Открыть презентацию", "", "PowerPoint Files (*.pptx)")
        if file:
            self.selected_file = file
            self.btn_start.setEnabled(True)
            self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
            self.log_output.clear()
            self.update_log(f"✅ Выбрана презентация: {self.selected_file}")

    def run_translation(self):
        """Запуск процесса в отдельном потоке."""
        self.btn_start.setEnabled(False)
        self.btn_browse.setEnabled(False)
        
        self.worker = TranslationWorker(self.selected_file)
        self.worker.log_signal.connect(self.update_log)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.finished.connect(self.worker.deleteLater) 
        self.worker.start()

    def update_log(self, text):
        """Добавление текста в лог и автоматическая прокрутка."""
        self.log_output.append(text)
        self.log_output.ensureCursorVisible()

    def on_finished(self):
        """Разблокировка интерфейса по завершении."""
        self.btn_start.setEnabled(True)
        self.btn_browse.setEnabled(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
