# -*- coding: utf-8 -*-
# modules/sales_functions_dialog.py
from PyQt5.QtWidgets import (
    QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, 
    QFrame, QShortcut, QApplication, QGridLayout
)
from PyQt5.QtGui import QFont, QKeySequence
from PyQt5.QtCore import Qt, QPoint

class SalesFunctionsDialog(QDialog):
    """
    Diálogo modal para agrupar funções secundárias do PDV
    (Desconto Item, Desconto Venda, Mov. Caixa).
    """
    def __init__(self, parent, permissions):
        super().__init__(parent)
        
        self.result_action = None # 'DESCONTO_ITEM', 'DESCONTO_VENDA', 'MOV_CAIXA'
        self.old_pos = None
        self.permissions = permissions
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)
        self.setFixedSize(450, 300)
        
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
        title_layout.addWidget(QLabel("Funções do PDV", objectName="title_label"))
        title_layout.addStretch()
        
        main_layout.addWidget(self.title_bar)

        # 2. Botões de Ação
        btn_layout = QGridLayout()
        btn_layout.setContentsMargins(15, 15, 15, 10)
        btn_layout.setSpacing(10)
        
        self.btn_desc_item = QPushButton("Desconto no Item (F5)")
        self.btn_desc_item.setObjectName("btn_funcao")
        self.btn_desc_item.setMinimumHeight(60)
        self.btn_desc_item.clicked.connect(self.accept_desconto_item)
        
        self.btn_desc_venda = QPushButton("Desconto na Venda (F6)")
        self.btn_desc_venda.setObjectName("btn_funcao")
        self.btn_desc_venda.setMinimumHeight(60)
        self.btn_desc_venda.clicked.connect(self.accept_desconto_venda)
        
        self.btn_mov_caixa = QPushButton("Mov. Caixa (F7)")
        self.btn_mov_caixa.setObjectName("btn_funcao")
        self.btn_mov_caixa.setMinimumHeight(60)
        self.btn_mov_caixa.clicked.connect(self.accept_mov_caixa)
        
        self.btn_cancelar = QPushButton("Cancelar (Esc)")
        self.btn_cancelar.setObjectName("btn_cancelar")
        self.btn_cancelar.setMinimumHeight(60)
        self.btn_cancelar.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.btn_desc_item, 0, 0)
        btn_layout.addWidget(self.btn_desc_venda, 1, 0)
        btn_layout.addWidget(self.btn_mov_caixa, 0, 1)
        btn_layout.addWidget(self.btn_cancelar, 1, 1)
        
        # Aplica permissões
        self.btn_desc_item.setEnabled(self.permissions.get("pode_desconto_item", False))
        self.btn_desc_venda.setEnabled(self.permissions.get("pode_desconto_venda", False))
        self.btn_mov_caixa.setEnabled(self.permissions.get("pode_mov_caixa", False))
        
        main_layout.addLayout(btn_layout)
        
        # Atalhos
        self.sc_f5 = QShortcut(QKeySequence("F5"), self)
        self.sc_f5.activated.connect(self.btn_desc_item.click)
        
        self.sc_f6 = QShortcut(QKeySequence("F6"), self)
        self.sc_f6.activated.connect(self.btn_desc_venda.click)
        
        self.sc_f7 = QShortcut(QKeySequence("F7"), self)
        self.sc_f7.activated.connect(self.btn_mov_caixa.click)

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
            QPushButton#btn_funcao { background-color: #f39c12; color: white; }
            QPushButton#btn_funcao:hover { background-color: #e67e22; }
            QPushButton#btn_funcao:disabled { background-color: #aaa; color: #eee; }
            
            QPushButton#btn_cancelar { background-color: #e74c3c; color: white; }
            QPushButton#btn_cancelar:hover { background-color: #c0392b; }
        """)
        
    def accept_desconto_item(self):
        if not self.btn_desc_item.isEnabled(): return
        self.result_action = 'DESCONTO_ITEM'
        self.accept()

    def accept_desconto_venda(self):
        if not self.btn_desc_venda.isEnabled(): return
        self.result_action = 'DESCONTO_VENDA'
        self.accept()
        
    def accept_mov_caixa(self):
        if not self.btn_mov_caixa.isEnabled(): return
        self.result_action = 'MOV_CAIXA'
        self.accept()
        
    def get_result(self):
        return self.result_action
        
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