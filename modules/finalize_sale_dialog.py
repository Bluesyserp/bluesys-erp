# -*- coding: utf-8 -*-
# modules/finalize_sale_dialog.py
from PyQt5.QtWidgets import (
    QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, 
    QFrame, QShortcut, QApplication
)
from PyQt5.QtGui import QFont, QKeySequence
from PyQt5.QtCore import Qt, QPoint

class FinalizeSaleDialog(QDialog):
    """
    Diálogo modal para escolher entre finalização Fiscal ou Não-Fiscal.
    """
    def __init__(self, parent=None, habilita_nao_fiscal=True, is_prevenda=False):
        super().__init__(parent)
        
        self.result_type = None # 'FISCAL' ou 'NAO_FISCAL'
        self.old_pos = None
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)
        
        # Ajusta o tamanho se o botão não-fiscal não estiver visível
        self.setFixedSize(400, 200 if habilita_nao_fiscal and not is_prevenda else 150)
        
        self._setup_styles()
        
        # Layout Principal (Container)
        main_frame = QFrame(self)
        main_frame.setObjectName("main_frame")
        main_layout = QVBoxLayout(main_frame)
        main_layout.setContentsMargins(0, 0, 0, 15)
        
        # 1. Barra de Título
        self.title_bar = QFrame()
        self.title_bar.setObjectName("title_bar")
        self.title_bar.setFixedHeight(35)
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(10, 0, 10, 0)
        title_layout.addWidget(QLabel("Finalizar Venda", objectName="title_label"))
        title_layout.addStretch()
        
        main_layout.addWidget(self.title_bar)

        # 2. Botões de Ação
        btn_layout = QVBoxLayout()
        btn_layout.setContentsMargins(15, 15, 15, 10)
        btn_layout.setSpacing(10)
        
        self.btn_fiscal = QPushButton("EMITIR DOCUMENTO FISCAL (F10)")
        self.btn_fiscal.setObjectName("btn_fiscal")
        self.btn_fiscal.setMinimumHeight(50)
        self.btn_fiscal.clicked.connect(self.accept_fiscal)
        
        self.btn_nao_fiscal = QPushButton("EMITIR DOCUMENTO NÃO-FISCAL (F9)")
        self.btn_nao_fiscal.setObjectName("btn_nao_fiscal")
        self.btn_nao_fiscal.setMinimumHeight(50)
        self.btn_nao_fiscal.clicked.connect(self.accept_nao_fiscal)
        
        btn_layout.addWidget(self.btn_fiscal)
        
        # Só mostra o botão Não-Fiscal se estiver habilitado E se não for uma pré-venda
        if habilita_nao_fiscal and not is_prevenda:
            btn_layout.addWidget(self.btn_nao_fiscal)
        elif is_prevenda:
             self.title_label.setText("Converter Venda Não-Fiscal")
             self.btn_fiscal.setText("Converter em Fiscal (F10)")
        
        main_layout.addLayout(btn_layout)
        
        # Atalhos
        self.sc_f10 = QShortcut(QKeySequence("F10"), self)
        self.sc_f10.activated.connect(self.accept_fiscal)
        
        self.sc_f9 = QShortcut(QKeySequence("F9"), self)
        self.sc_f9.activated.connect(self.accept_nao_fiscal)

        self.sc_esc = QShortcut(QKeySequence("Esc"), self)
        self.sc_esc.activated.connect(self.reject)
        
        dialog_layout = QVBoxLayout(self)
        dialog_layout.setContentsMargins(0,0,0,0)
        dialog_layout.addWidget(main_frame)
        
        # Centraliza no pai
        if parent:
            parent_global_center = parent.mapToGlobal(parent.rect().center())
            self.move(parent_global_center - self.rect().center())
        
    def _setup_styles(self):
        self.setStyleSheet("""
            QDialog { background-color: transparent; }
            QFrame#main_frame {
                background-color: #f8f8fb; border-radius: 8px; border: 1px solid #c0c0d0;
            }
            QFrame#title_bar {
                background-color: #e0e8f0; border-top-left-radius: 8px;
                border-top-right-radius: 8px; border-bottom: 1px solid #c0c0d0;
            }
            QLabel#title_label { font-size: 14px; font-weight: bold; color: #333; }
            QPushButton {
                padding: 8px 15px; font-weight: bold; border-radius: 6px;
                font-size: 14px;
            }
            QPushButton#btn_fiscal { background-color: #0078d7; color: white; }
            QPushButton#btn_fiscal:hover { background-color: #005fa3; }
            
            QPushButton#btn_nao_fiscal { background-color: #27AE60; color: white; }
            QPushButton#btn_nao_fiscal:hover { background-color: #229954; }
        """)
        
    def accept_fiscal(self):
        self.result_type = 'FISCAL'
        self.accept()

    def accept_nao_fiscal(self):
        self.result_type = 'NAO_FISCAL'
        self.accept()
        
    def get_result(self):
        return self.result_type
        
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