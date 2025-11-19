# modules/pos_auth_dialog.py
from PyQt5.QtWidgets import (
    QDialog, QLabel, QLineEdit, QPushButton, 
    QVBoxLayout, QHBoxLayout, QFrame, QGridLayout,
    QMessageBox, QDoubleSpinBox
)
from PyQt5.QtGui import QFont, QDoubleValidator
from PyQt5.QtCore import Qt, QLocale, QPoint

# --- FUNÇÃO 'center_dialog' REMOVIDA DESTE LOCAL ---

class PosAuthDialog(QDialog):
    def __init__(self, valor_restante, parent=None):
        super().__init__(parent)
        
        self.valor_autorizado = 0.0
        self.nsu = ""
        self.doc = ""
        self.old_pos = None
        self._centered = False # Flag para centralizar apenas uma vez
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog) # Adiciona | Qt.Dialog
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(350, 280)
        self.setModal(True)

        locale = QLocale(QLocale.Portuguese, QLocale.Brazil)
        self.validator = QDoubleValidator(0.01, 99999.99, 2)
        self.validator.setLocale(locale)
        self.validator.setNotation(QDoubleValidator.StandardNotation)
        
        self._setup_styles()
        
        # Layout Principal (Container)
        main_frame = QFrame(self)
        main_frame.setObjectName("main_frame")
        main_layout = QVBoxLayout(main_frame)
        main_layout.setContentsMargins(0, 0, 0, 10)
        
        # 1. Barra de Título
        self.title_bar = QFrame()
        self.title_bar.setObjectName("title_bar")
        self.title_bar.setFixedHeight(35)
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(10, 0, 10, 0)
        title_layout.addWidget(QLabel("Autorização POS", objectName="title_label"))
        title_layout.addStretch()
        
        main_layout.addWidget(self.title_bar)

        # 2. Formulário
        form_layout = QGridLayout()
        form_layout.setContentsMargins(15, 15, 15, 15)
        form_layout.setSpacing(10)
        
        form_layout.addWidget(QLabel("Valor a Autorizar:"), 0, 0)
        self.valor_input = QDoubleSpinBox()
        self.valor_input.setRange(0.01, 99999.99)
        self.valor_input.setValue(valor_restante)
        self.valor_input.setButtonSymbols(QDoubleSpinBox.NoButtons)
        self.valor_input.setFont(QFont("Segoe UI", 12, QFont.Bold))
        form_layout.addWidget(self.valor_input, 0, 1)

        form_layout.addWidget(QLabel("NSU (Autenticação):"), 1, 0)
        self.nsu_input = QLineEdit()
        self.nsu_input.setPlaceholderText("NSU da maquininha")
        self.nsu_input.setFocus() # Foca neste campo
        form_layout.addWidget(self.nsu_input, 1, 1)

        form_layout.addWidget(QLabel("Nº Documento:"), 2, 0)
        self.doc_input = QLineEdit()
        self.doc_input.setPlaceholderText("Nº Doc da maquininha")
        form_layout.addWidget(self.doc_input, 2, 1)
        
        main_layout.addLayout(form_layout)
        main_layout.addStretch()

        # 3. Botões
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(15, 0, 15, 0)
        btn_layout.addStretch()
        
        self.btn_cancelar = QPushButton("Cancelar (Esc)")
        self.btn_cancelar.setObjectName("btn_cancelar")
        self.btn_cancelar.setShortcut("Esc")
        self.btn_cancelar.clicked.connect(self.reject)
        
        self.btn_confirmar = QPushButton("Confirmar (ENTER)")
        self.btn_confirmar.setObjectName("btn_confirmar")
        self.btn_confirmar.setShortcut("Return")
        self.btn_confirmar.clicked.connect(self.confirm_and_accept)
        
        btn_layout.addWidget(self.btn_cancelar)
        btn_layout.addWidget(self.btn_confirmar)
        main_layout.addLayout(btn_layout)
        
        # Layout container para o QDialog
        dialog_layout = QVBoxLayout(self)
        dialog_layout.setContentsMargins(0,0,0,0)
        dialog_layout.addWidget(main_frame)
        
        # --- CHAMADA 'center_dialog' REMOVIDA DAQUI ---

    # --- NOVO MÉTODO: showEvent ---
    def showEvent(self, event):
        """ Centraliza a janela no pai antes de mostrá-la. """
        super().showEvent(event)
        if self.parent() and not self._centered:
            # Pega o centro do 'parent' (PaymentDialog) em coordenadas GLOBAIS (da tela)
            parent_global_center = self.parent().mapToGlobal(self.parent().rect().center())
            # Pega o centro do 'dialog' (PosAuthDialog)
            dialog_center = self.rect().center()
            # Move o 'dialog' para que seu centro se alinhe ao centro do 'parent'
            self.move(parent_global_center - dialog_center)
            self._centered = True
    # --- FIM DA CORREÇÃO ---
    
    def _setup_styles(self):
        self.setStyleSheet("""
            QDialog { background-color: transparent; }
            QFrame#main_frame {
                background-color: #f8f8fb;
                border-radius: 8px;
                border: 1px solid #c0c0d0;
            }
            QFrame#title_bar {
                background-color: #e0e8f0;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                border-bottom: 1px solid #c0c0d0;
            }
            QLabel#title_label { font-size: 14px; font-weight: bold; color: #333; }
            QLabel { font-size: 13px; color: #444; }
            QLineEdit, QDoubleSpinBox {
                border: 1px solid #c0c0d0; border-radius: 5px; 
                padding: 6px; background-color: white;
            }
            QPushButton {
                padding: 8px 15px; font-weight: bold; border-radius: 6px;
            }
            QPushButton#btn_confirmar { background-color: #0078d7; color: white; }
            QPushButton#btn_confirmar:hover { background-color: #005fa3; }
            QPushButton#btn_cancelar { background-color: #e74c3c; color: white; }
            QPushButton#btn_cancelar:hover { background-color: #c0392b; }
        """)
        
    def confirm_and_accept(self):
        nsu = self.nsu_input.text().strip()
        doc = self.doc_input.text().strip()
        valor = self.valor_input.value()
        
        if not nsu or not doc:
            QMessageBox.warning(self, "Campos Obrigatórios", 
                "Os campos NSU e Nº Documento são obrigatórios para pagamentos POS.")
            return
            
        self.valor_autorizado = valor
        self.nsu = nsu
        self.doc = doc
        self.accept()

    def get_data(self):
        return self.valor_autorizado, self.nsu, self.doc
        
    # --- Métodos para Mover a Janela ---
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.title_bar.geometry().contains(event.pos()):
            self.old_pos = event.globalPos()

    def mouseMoveEvent(self, event):
        if self.old_pos and event.buttons() == Qt.LeftButton:
            delta = QPoint(event.globalPos() - self.old_pos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPos()

    def mouseReleaseEvent(self, event):
        self.old_pos = None