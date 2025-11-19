# modules/open_cash_dialog.py
from PyQt5.QtWidgets import QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout, QMessageBox
from PyQt5.QtGui import QDoubleValidator, QFont
from PyQt5.QtCore import Qt, QLocale

class OpenCashDialog(QDialog):
    def __init__(self, terminal_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Abrir Caixa")
        self.setModal(True)
        self.setFixedSize(350, 200)
        
        # Validador
        locale = QLocale(QLocale.Portuguese, QLocale.Brazil)
        self.validator = QDoubleValidator(0.00, 99999.99, 2)
        self.validator.setLocale(locale)
        self.validator.setNotation(QDoubleValidator.StandardNotation)

        layout = QVBoxLayout(self)
        
        # --- NOVO LABEL DO TERMINAL ---
        terminal_label = QLabel(f"Terminal: {terminal_name}")
        terminal_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #005fa3;")
        layout.addWidget(terminal_label)
        # --- FIM DA ALTERAÇÃO ---
        
        layout.addWidget(QLabel("Informe o valor inicial do caixa (suprimento):"))
        
        self.valor_input = QLineEdit("0,00")
        self.valor_input.setValidator(self.validator)
        self.valor_input.setFont(QFont("Arial", 12))
        self.valor_input.selectAll()
        self.valor_input.setFocus()
        layout.addWidget(self.valor_input)
        
        self.ok_btn = QPushButton("Abrir Caixa (F10)")
        self.ok_btn.setShortcut("F10")
        self.ok_btn.clicked.connect(self.accept)
        layout.addWidget(self.ok_btn)

    def get_value(self):
        """Retorna o valor digitado como float."""
        try:
            valor_str = self.valor_input.text().replace(',', '.')
            return float(valor_str)
        except ValueError:
            return 0.0