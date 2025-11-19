# -*- coding: utf-8 -*-
# modules/motivos_cancelamento_form.py
import sqlite3
import logging
from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, 
    QMessageBox, QGridLayout, QFrame, QTableWidget, QHeaderView, 
    QTableWidgetItem, QAbstractItemView, QCheckBox
)
from PyQt5.QtCore import Qt
from database.db import get_connection

class MotivosCancelamentoForm(QWidget):
    """
    Formulário para Gestão de Motivos de Cancelamento.
    Configuração geral do sistema (Módulo Comercial).
    """
    def __init__(self, user_id, **kwargs):
        super().__init__()
        self.user_id = user_id
        self.setWindowTitle("Motivos de Cancelamento")
        
        self.current_motivo_id = None
        self.logger = logging.getLogger(__name__)
        
        self._setup_styles()
        self._build_ui()
        self._connect_signals()
        
        self.load_data()
        self.set_mode(0) # Modo Lista

    def _setup_styles(self):
        self.setStyleSheet("""
            QWidget { background-color: #f8f8fb; font-family: 'Segoe UI'; }
            QLabel { font-weight: bold; color: #444; font-size: 13px; }
            QTableWidget {
                border: 1px solid #c0c0d0;
                selection-background-color: #0078d7;
                font-size: 14px;
            }
            QHeaderView::section {
                background-color: #e8e8e8; padding: 8px;
                border: 1px solid #c0c0d0;
                font-weight: bold; font-size: 14px;
            }
            QFrame#form_panel {
                background-color: #fdfdfd;
                border: 1px solid #c0c0d0;
                border-radius: 8px;
            }
            QLineEdit {
                border: 1px solid #c0c0d0; border-radius: 5px; 
                padding: 6px; background-color: white; font-size: 13px;
            }
            QPushButton {
                background-color: #0078d7; color: white; border-radius: 6px;
                padding: 8px 15px; font-weight: bold;
            }
            QPushButton:hover { background-color: #005fa3; }
            QPushButton#deleteButton { background-color: #e74c3c; }
            QPushButton#deleteButton:hover { background-color: #c0392b; }
            QPushButton#cancelButton { background-color: #95A5A6; }
            QPushButton#cancelButton:hover { background-color: #7F8C8D; }
        """)

    def _build_ui(self):
        main_layout = QHBoxLayout(self)
        
        # --- Coluna Esquerda: Lista ---
        left_layout = QVBoxLayout()
        
        self.btn_novo = QPushButton("Novo Motivo")
        left_layout.addWidget(self.btn_novo)
        
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["ID", "Descrição", "Ativo"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setColumnHidden(0, True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        left_layout.addWidget(self.table)
        
        main_layout.addLayout(left_layout, 1)
        
        # --- Coluna Direita: Formulário ---
        self.form_panel = QFrame()
        self.form_panel.setObjectName("form_panel")
        self.form_panel.setFixedWidth(350)
        form_layout = QVBoxLayout(self.form_panel)
        
        self.lbl_title = QLabel("Novo Motivo")
        self.lbl_title.setStyleSheet("font-size: 16px; color: #005fa3; margin-bottom: 10px;")
        form_layout.addWidget(self.lbl_title)
        
        form_layout.addWidget(QLabel("Descrição do Motivo:"))
        self.descricao_input = QLineEdit()
        form_layout.addWidget(self.descricao_input)
        
        self.ativo_check = QCheckBox("Ativo")
        self.ativo_check.setChecked(True)
        form_layout.addWidget(self.ativo_check)
        
        form_layout.addStretch()
        
        btn_row = QHBoxLayout()
        self.btn_salvar = QPushButton("Salvar")
        self.btn_excluir = QPushButton("Excluir")
        self.btn_excluir.setObjectName("deleteButton")
        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.setObjectName("cancelButton")
        
        btn_row.addWidget(self.btn_cancelar)
        btn_row.addWidget(self.btn_excluir)
        btn_row.addWidget(self.btn_salvar)
        form_layout.addLayout(btn_row)
        
        main_layout.addWidget(self.form_panel)

    def _connect_signals(self):
        self.btn_novo.clicked.connect(self.new_motivo)
        self.btn_salvar.clicked.connect(self.save_motivo)
        self.btn_excluir.clicked.connect(self.delete_motivo)
        self.btn_cancelar.clicked.connect(lambda: self.set_mode(0))
        self.table.itemDoubleClicked.connect(self.load_selected)

    def set_mode(self, mode):
        """0 = Navegação, 1 = Edição/Criação"""
        if mode == 0:
            self.form_panel.setEnabled(False)
            self.descricao_input.clear()
            self.ativo_check.setChecked(True)
            self.current_motivo_id = None
            self.lbl_title.setText("Selecione ou Crie")
            self.table.clearSelection()
        else:
            self.form_panel.setEnabled(True)
            self.descricao_input.setFocus()

    def load_data(self):
        self.table.setRowCount(0)
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM motivos_cancelamento ORDER BY descricao")
            rows = cur.fetchall()
            
            for r in rows:
                idx = self.table.rowCount()
                self.table.insertRow(idx)
                self.table.setItem(idx, 0, QTableWidgetItem(str(r['id'])))
                self.table.setItem(idx, 1, QTableWidgetItem(r['descricao']))
                status = "Sim" if r['ativo'] else "Não"
                self.table.setItem(idx, 2, QTableWidgetItem(status))
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao carregar motivos: {e}")
        finally:
            conn.close()

    def new_motivo(self):
        self.set_mode(1)
        self.lbl_title.setText("Novo Motivo")
        self.btn_excluir.setEnabled(False)

    def load_selected(self, item):
        row = item.row()
        id_motivo = int(self.table.item(row, 0).text())
        
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM motivos_cancelamento WHERE id = ?", (id_motivo,))
            data = cur.fetchone()
            if data:
                self.current_motivo_id = data['id']
                self.descricao_input.setText(data['descricao'])
                self.ativo_check.setChecked(bool(data['ativo']))
                
                self.set_mode(1)
                self.lbl_title.setText("Editando Motivo")
                self.btn_excluir.setEnabled(True)
        finally:
            conn.close()

    def save_motivo(self):
        desc = self.descricao_input.text().strip()
        if not desc:
            QMessageBox.warning(self, "Aviso", "A descrição é obrigatória.")
            return
            
        ativo = 1 if self.ativo_check.isChecked() else 0
        
        conn = get_connection()
        try:
            cur = conn.cursor()
            if self.current_motivo_id:
                cur.execute("UPDATE motivos_cancelamento SET descricao=?, ativo=? WHERE id=?", (desc, ativo, self.current_motivo_id))
                action = "ATUALIZOU"
            else:
                cur.execute("INSERT INTO motivos_cancelamento (descricao, ativo) VALUES (?, ?)", (desc, ativo))
                self.current_motivo_id = cur.lastrowid
                action = "CRIOU"
            
            conn.commit()
            self.logger.info(f"Usuário {self.user_id} {action} motivo cancelamento: '{desc}'.")
            
            QMessageBox.information(self, "Sucesso", "Motivo salvo com sucesso.")
            self.load_data()
            self.set_mode(0)
            
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "Erro", "Já existe um motivo com essa descrição.")
        except Exception as e:
            self.logger.error(f"Erro ao salvar motivo: {e}", exc_info=True)
            QMessageBox.critical(self, "Erro", f"Erro ao salvar: {e}")
        finally:
            conn.close()

    def delete_motivo(self):
        if not self.current_motivo_id: return
        
        reply = QMessageBox.question(self, "Confirmar", "Tem certeza que deseja excluir este motivo?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.No: return
        
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM motivos_cancelamento WHERE id = ?", (self.current_motivo_id,))
            conn.commit()
            
            self.logger.info(f"Usuário {self.user_id} EXCLUIU motivo cancelamento ID {self.current_motivo_id}.")
            
            QMessageBox.information(self, "Sucesso", "Motivo excluído.")
            self.load_data()
            self.set_mode(0)
        except Exception as e:
            self.logger.error(f"Erro ao excluir motivo: {e}", exc_info=True)
            QMessageBox.critical(self, "Erro", f"Erro ao excluir: {e}")
        finally:
            conn.close()