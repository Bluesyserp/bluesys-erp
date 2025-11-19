# modules/custom_dialogs.py
from PyQt5.QtWidgets import (
    QDialog, QLabel, QLineEdit, QPushButton, 
    QVBoxLayout, QHBoxLayout, QFrame, QComboBox, 
    QSpinBox, QDialogButtonBox, QApplication
)
from PyQt5.QtCore import Qt, QPoint

class FramelessDialog(QDialog):
    """ Classe base para todos os diálogos personalizados 'sem borda' """
    def __init__(self, parent=None, title="Aviso"):
        super().__init__(parent)
        self.old_pos = None
        self._centered = False # Flag para centralizar apenas uma vez

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)
        
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
                height: 35px;
            }
            QLabel#title_label { font-size: 14px; font-weight: bold; color: #333; padding-left: 10px; }
            QLabel.dialog_label { font-size: 13px; color: #333; margin-bottom: 5px; }
            QLineEdit, QComboBox, QSpinBox {
                border: 1px solid #c0c0d0; border-radius: 5px; 
                padding: 6px; background-color: white; font-size: 13px;
            }
            QPushButton {
                padding: 8px 15px; font-weight: bold; border-radius: 6px;
                font-size: 13px;
            }
            QPushButton[text="OK"], QPushButton[text="Confirmar"] { 
                background-color: #0078d7; color: white; 
            }
            QPushButton[text="OK"]:hover, QPushButton[text="Confirmar"]:hover { 
                background-color: #005fa3; 
            }
            QPushButton[text="Cancel"], QPushButton[text="Cancelar"] { 
                background-color: #e74c3c; color: white; 
            }
            QPushButton[text="Cancel"]:hover, QPushButton[text="Cancelar"]:hover { 
                background-color: #c0392b; 
            }
        """)

        # --- Layout Principal ---
        self.main_frame = QFrame(self)
        self.main_frame.setObjectName("main_frame")
        self.main_layout = QVBoxLayout(self.main_frame)
        self.main_layout.setContentsMargins(1, 1, 1, 10) 
        self.main_layout.setSpacing(10)

        # 1. Barra de Título
        self.title_bar = QFrame()
        self.title_bar.setObjectName("title_bar")
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(10, 0, 10, 0)
        self.title_label = QLabel(title, objectName="title_label")
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()
        self.main_layout.addWidget(self.title_bar)

        # 2. Área de Conteúdo (será preenchida pelas subclasses)
        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(15, 10, 15, 10)
        self.main_layout.addLayout(self.content_layout)

        # 3. Botões (OK/Cancelar)
        self.button_box = QDialogButtonBox()
        self.ok_button = self.button_box.addButton("OK", QDialogButtonBox.AcceptRole)
        self.cancel_button = self.button_box.addButton("Cancel", QDialogButtonBox.RejectRole)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(15, 0, 15, 0)
        btn_layout.addStretch()
        btn_layout.addWidget(self.button_box)
        self.main_layout.addLayout(btn_layout)

        # Layout final do QDialog
        dialog_layout = QVBoxLayout(self)
        dialog_layout.setContentsMargins(0, 0, 0, 0)
        dialog_layout.addWidget(self.main_frame)
        
    def showEvent(self, event):
        """ Centraliza a janela no pai antes de mostrá-la. """
        super().showEvent(event)
        if self.parent() and not self._centered:
            parent_global_center = self.parent().mapToGlobal(self.parent().rect().center())
            self.move(parent_global_center - self.rect().center())
            self._centered = True 

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

class CustomComboDialog(FramelessDialog):
    """ Substituto para QInputDialog.getItem """
    def __init__(self, parent, title, label, items, current=0):
        super().__init__(parent, title)
        self.setFixedSize(350, 160)
        
        self.content_layout.addWidget(QLabel(label, objectName="dialog_label"))
        self.combo_box = QComboBox()
        self.combo_box.addItems(items)
        self.combo_box.setCurrentIndex(current)
        self.content_layout.addWidget(self.combo_box)
        self.combo_box.setFocus()
        
    def get_selected_item(self):
        return self.combo_box.currentText()

class CustomIntDialog(FramelessDialog):
    """ Substituto para QInputDialog.getInt """
    def __init__(self, parent, title, label, value=1, min_val=1, max_val=99, step=1):
        super().__init__(parent, title)
        self.setFixedSize(350, 160)
        
        self.content_layout.addWidget(QLabel(label, objectName="dialog_label"))
        self.spin_box = QSpinBox()
        self.spin_box.setRange(min_val, max_val)
        self.spin_box.setValue(value)
        self.spin_box.setSingleStep(step)
        self.content_layout.addWidget(self.spin_box)
        self.spin_box.setFocus()
        self.spin_box.selectAll()

    def get_value(self):
        return self.spin_box.value()

class CustomInputDialog(FramelessDialog):
    """ Substituto para QInputDialog.getText """
    def __init__(self, parent, title, label, text="", echo_mode=QLineEdit.Normal):
        super().__init__(parent, title)
        self.setFixedSize(380, 160)
        
        self.content_layout.addWidget(QLabel(label, objectName="dialog_label"))
        self.line_edit = QLineEdit(text)
        self.line_edit.setEchoMode(echo_mode)
        self.content_layout.addWidget(self.line_edit)
        self.line_edit.setFocus()
        self.line_edit.selectAll()

    def get_text(self):
        return self.line_edit.text()