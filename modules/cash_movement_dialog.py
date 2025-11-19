# modules/cash_movement_dialog.py
from PyQt5.QtWidgets import (
    QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, 
    QFrame, QGridLayout, QMessageBox, QDoubleSpinBox,
    QTextEdit, QComboBox
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QPoint
from .custom_dialogs import FramelessDialog 

class CashMovementDialog(FramelessDialog):
    """
    Diálogo para registrar Sangria (Saída) ou Suprimento (Entrada) no caixa.
    """
    def __init__(self, parent=None):
        super().__init__(parent, title="Movimentação de Caixa")
        
        self.setFixedSize(400, 300)
        
        # Altera os botões padrão
        self.ok_button.setText("Confirmar")
        self.cancel_button.setText("Cancelar")
        
        self._build_ui()
        
    def _build_ui(self):
        grid = QGridLayout()
        grid.setSpacing(10)
        
        grid.addWidget(QLabel("Tipo de Movimento:", objectName="dialog_label"), 0, 0)
        self.tipo_combo = QComboBox()
        self.tipo_combo.addItems(["SANGRIA (Saída)", "SUPRIMENTO (Entrada)"])
        grid.addWidget(self.tipo_combo, 0, 1)
        
        grid.addWidget(QLabel("Valor (R$):", objectName="dialog_label"), 1, 0)
        self.valor_spinbox = QDoubleSpinBox()
        self.valor_spinbox.setRange(0.01, 99999.99)
        self.valor_spinbox.setButtonSymbols(QDoubleSpinBox.NoButtons)
        self.valor_spinbox.setSingleStep(50)
        self.valor_spinbox.setAlignment(Qt.AlignRight)
        self.valor_spinbox.setFont(QFont("Segoe UI", 12, QFont.Bold))
        grid.addWidget(self.valor_spinbox, 1, 1)
        
        grid.addWidget(QLabel("Motivo/Observação:", objectName="dialog_label"), 2, 0, Qt.AlignTop)
        self.motivo_text = QTextEdit()
        self.motivo_text.setFixedHeight(80)
        self.motivo_text.setStyleSheet("font-size: 13px;")
        grid.addWidget(self.motivo_text, 2, 1)
        
        # Adiciona o grid ao layout de conteúdo (da classe base)
        self.content_layout.addLayout(grid)
        
        self.valor_spinbox.setFocus()

    def get_data(self):
        """Retorna os dados inseridos no diálogo."""
        valor = self.valor_spinbox.value()
        if valor < 0.01:
            QMessageBox.warning(self, "Valor Inválido", "O valor da movimentação deve ser maior que zero.")
            return None
            
        tipo = "SANGRIA" if self.tipo_combo.currentIndex() == 0 else "SUPRIMENTO"
        motivo = self.motivo_text.toPlainText().strip()
        
        if not motivo:
             QMessageBox.warning(self, "Campo Obrigatório", "O campo Motivo/Observação é obrigatório.")
             return None
             
        return {
            "tipo": tipo,
            "valor": valor,
            "motivo": motivo
        }