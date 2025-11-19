# -*- coding: utf-8 -*-
# modules/centros_custo_form.py
import sqlite3
import logging # <-- NOVO
from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, 
    QMessageBox, QGridLayout, QFrame, QTableWidget, QHeaderView, 
    QTableWidgetItem, QAbstractItemView, QStackedWidget, QComboBox
)
from PyQt5.QtCore import Qt
from database.db import get_connection

class CentrosCustoForm(QWidget):
    """
    Formulário para CRUD de Centros de Custo.
    Req. #9 do Módulo Financeiro.
    """
    def __init__(self, user_id, **kwargs):
        super().__init__()
        self.user_id = user_id
        self.current_centro_id = None
        self.setWindowTitle("Cadastro de Centros de Custo")
        
        # --- NOVO: Logger ---
        self.logger = logging.getLogger(__name__)
        
        self.company_map = {} # {id_empresa: razao_social}
        
        self._setup_styles()
        self._build_ui()
        self._connect_signals()
        
        self.set_mode(0) # Começa na lista

    def _setup_styles(self):
        self.setStyleSheet("""
            QWidget { background-color: #f8f8fb; font-family: 'Segoe UI'; }
            QLabel { font-weight: bold; color: #444; font-size: 13px; }
            QLabel.required::after { content: " *"; color: #e74c3c; }
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
            QLabel#form_title {
                font-size: 16px; font-weight: bold; color: #005fa3;
                padding: 5px; border-bottom: 1px solid #eee;
            }
            
            QLineEdit, QComboBox {
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
        main_layout = QVBoxLayout(self)
        
        # --- 1. PAINEL DE BUSCA E NAVEGAÇÃO ---
        self.search_panel = QWidget()
        search_layout = QHBoxLayout(self.search_panel)
        search_layout.setContentsMargins(0, 10, 0, 10)
        self.btn_novo = QPushButton("Novo Centro de Custo")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Pesquisar por Nome ou Código...")
        self.btn_pesquisar = QPushButton("Pesquisar")
        
        search_layout.addWidget(self.btn_novo)
        search_layout.addStretch()
        search_layout.addWidget(self.search_input, 1) 
        search_layout.addWidget(self.btn_pesquisar)
        
        # --- 2. STACKED WIDGET (Tabela / Formulário) ---
        self.stack = QStackedWidget()
        
        # --- Tela 0: Tabela de Centros de Custo ---
        self.table_widget = QWidget()
        table_layout = QVBoxLayout(self.table_widget)
        table_layout.setContentsMargins(0,0,0,0)
        self.centro_table = QTableWidget()
        self.centro_table.setColumnCount(4)
        self.centro_table.setHorizontalHeaderLabels(["ID", "Nome do Centro de Custo", "Código", "Empresa"])
        self.centro_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.centro_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.centro_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.centro_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.centro_table.setColumnHidden(0, True)
        table_layout.addWidget(self.centro_table)
        
        # --- Tela 1: Formulário de Cadastro ---
        self.form_panel = QFrame()
        self.form_panel.setObjectName("form_panel")
        form_layout = QVBoxLayout(self.form_panel)
        self.form_title = QLabel("Cadastro de Centro de Custo", objectName="form_title")
        form_layout.addWidget(self.form_title)
        
        form_grid = QGridLayout()
        form_grid.setSpacing(10)
        
        self.empresa_combo = QComboBox()
        self.nome_input = QLineEdit()
        self.codigo_input = QLineEdit()
        self.codigo_input.setPlaceholderText("Ex: 1.01.01, ADM, LOJA (Opcional)")
        
        form_grid.addWidget(QLabel("Empresa: *", objectName="required"), 0, 0)
        form_grid.addWidget(self.empresa_combo, 0, 1)
        form_grid.addWidget(QLabel("Nome do Centro de Custo: *", objectName="required"), 1, 0)
        form_grid.addWidget(self.nome_input, 1, 1)
        form_grid.addWidget(QLabel("Código:"), 2, 0)
        form_grid.addWidget(self.codigo_input, 2, 1)
        
        form_grid.setColumnStretch(1, 1)
        form_layout.addLayout(form_grid)
        form_layout.addStretch()
        
        # Botões do formulário
        form_btn_layout = QHBoxLayout()
        form_btn_layout.addStretch()
        self.btn_salvar = QPushButton("Salvar")
        self.btn_excluir = QPushButton("Excluir")
        self.btn_excluir.setObjectName("deleteButton")
        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.setObjectName("cancelButton")
        form_btn_layout.addWidget(self.btn_cancelar)
        form_btn_layout.addWidget(self.btn_excluir)
        form_btn_layout.addWidget(self.btn_salvar)
        form_layout.addLayout(form_btn_layout)
        
        self.stack.addWidget(self.table_widget)
        self.stack.addWidget(self.form_panel)
        
        main_layout.addWidget(self.search_panel)
        main_layout.addWidget(self.stack, 1)

    def set_mode(self, mode):
        """Alterna entre o modo Tabela (0) e Formulário (1)."""
        if mode == 0:
            self.stack.setCurrentIndex(0)
            self.search_panel.setVisible(True)
            self.load_centros_custo() 
        else:
            self._load_empresas_combobox()
            self.stack.setCurrentIndex(1)
            self.search_panel.setVisible(False)

    def _connect_signals(self):
        self.btn_novo.clicked.connect(self.show_new_form)
        self.btn_salvar.clicked.connect(self.save_centro_custo)
        self.btn_excluir.clicked.connect(self.delete_centro_custo)
        self.btn_cancelar.clicked.connect(self.cancel_action)
        self.btn_pesquisar.clicked.connect(self.load_centros_custo)
        self.search_input.returnPressed.connect(self.load_centros_custo)
        self.centro_table.itemDoubleClicked.connect(self._load_centro_for_edit)

    def _load_empresas_combobox(self):
        self.empresa_combo.clear()
        self.company_map.clear()
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, razao_social FROM empresas WHERE status = 1 ORDER BY razao_social")
            empresas = cur.fetchall()
            
            self.empresa_combo.addItem("Selecione uma empresa...", None)
            if not empresas:
                self.empresa_combo.setEnabled(False)
                return

            self.empresa_combo.setEnabled(True)
            for empresa in empresas:
                self.empresa_combo.addItem(empresa['razao_social'], empresa['id'])
                self.company_map[empresa['id']] = empresa['razao_social']
            
            if self.empresa_combo.findData(1) >= 0:
                self.empresa_combo.setCurrentIndex(self.empresa_combo.findData(1))
        except Exception as e:
            self.logger.error(f"Erro ao carregar empresas: {e}", exc_info=True)
            QMessageBox.critical(self, "Erro", f"Erro ao carregar empresas: {e}")
        finally:
            conn.close()
            
    def load_centros_custo(self):
        """Carrega/Busca centros de custo e preenche a tabela."""
        self.centro_table.setRowCount(0)
        search_term = self.search_input.text().strip()
        
        conn = get_connection()
        try:
            if not self.company_map:
                cur_emp = conn.cursor()
                cur_emp.execute("SELECT id, razao_social FROM empresas")
                for emp in cur_emp.fetchall():
                    self.company_map[emp['id']] = emp['razao_social']

            cur = conn.cursor()
            query = "SELECT * FROM centros_de_custo"
            params = []
            
            if search_term:
                query += " WHERE (nome LIKE ? OR codigo LIKE ?)"
                params.extend([f"%{search_term}%", f"%{search_term}%"])
            
            query += " ORDER BY nome"
            cur.execute(query, tuple(params))
            
            rows = cur.fetchall()
            for row in rows:
                idx = self.centro_table.rowCount()
                self.centro_table.insertRow(idx)
                
                empresa_nome = self.company_map.get(row['empresa_id'], "Empresa Desconhecida")
                
                self.centro_table.setItem(idx, 0, QTableWidgetItem(str(row['id'])))
                self.centro_table.setItem(idx, 1, QTableWidgetItem(row['nome']))
                self.centro_table.setItem(idx, 2, QTableWidgetItem(row['codigo'] or "-"))
                self.centro_table.setItem(idx, 3, QTableWidgetItem(empresa_nome))
        
        except Exception as e:
            self.logger.error(f"Erro ao carregar Centros de Custo: {e}", exc_info=True)
            QMessageBox.critical(self, "Erro", f"Erro ao carregar Centros de Custo: {e}")
        finally:
            conn.close()

    def _load_centro_for_edit(self, item):
        """Carrega os dados do centro de custo selecionado no formulário."""
        row = item.row()
        centro_id = int(self.centro_table.item(row, 0).text())
        
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM centros_de_custo WHERE id = ?", (centro_id,))
            data = cur.fetchone()
            if not data:
                QMessageBox.critical(self, "Erro", "Centro de Custo não encontrado.")
                return

            self.clear_form()
            self.set_mode(1) 
            
            self.current_centro_id = centro_id
            self.form_title.setText(f"Editando Centro de Custo: {data['nome']}")
            
            index = self.empresa_combo.findData(data['empresa_id'])
            if index >= 0: self.empresa_combo.setCurrentIndex(index)
            
            self.nome_input.setText(data['nome'])
            self.codigo_input.setText(data['codigo'])
            
            self.btn_excluir.setEnabled(True)
            
        except Exception as e:
            self.logger.error(f"Erro ao carregar dados do centro de custo: {e}", exc_info=True)
            QMessageBox.critical(self, "Erro", f"Erro ao carregar dados: {e}")
        finally:
            conn.close()

    def show_new_form(self):
        self.clear_form()
        self.set_mode(1) 
        self.nome_input.setFocus()
        self.form_title.setText("Novo Centro de Custo")

    def cancel_action(self):
        self.clear_form()
        self.set_mode(0) 

    def clear_form(self):
        self.current_centro_id = None
        self.empresa_combo.setCurrentIndex(0)
        self.nome_input.clear()
        self.codigo_input.clear()
        
        self.btn_excluir.setEnabled(False)
        self.form_title.setText("Cadastro de Centro de Custo")

    def _validate_fields(self):
        if self.empresa_combo.currentData() is None:
            return False, "Empresa"
        if not self.nome_input.text().strip():
            return False, "Nome do Centro de Custo"
        return True, ""

    def save_centro_custo(self):
        valido, campo = self._validate_fields()
        if not valido:
            QMessageBox.warning(self, "Campo Obrigatório", f"O campo '{campo}' é obrigatório.")
            return

        data = {
            "empresa_id": self.empresa_combo.currentData(),
            "nome": self.nome_input.text().strip(),
            "codigo": self.codigo_input.text().strip() or None,
        }
        
        conn = get_connection()
        try:
            cur = conn.cursor()
            if self.current_centro_id:
                # UPDATE
                data["id"] = self.current_centro_id
                fields_to_update = [f"{key} = :{key}" for key in data.keys() if key != 'id']
                query = f"UPDATE centros_de_custo SET {', '.join(fields_to_update)} WHERE id = :id"
                params = data
                msg = "Centro de Custo atualizado!"
                action_verb = "ATUALIZOU"
            else:
                # INSERT
                fields = ", ".join(data.keys())
                placeholders = ", ".join([f":{k}" for k in data.keys()])
                query = f"INSERT INTO centros_de_custo ({fields}) VALUES ({placeholders})"
                params = data
                msg = "Centro de Custo salvo!"
                action_verb = "CRIOU"
            
            cur.execute(query, params)
            conn.commit()
            
            # --- LOG ADICIONADO ---
            self.logger.info(f"Usuário {self.user_id} {action_verb} centro de custo: '{data['nome']}' (Código: {data['codigo']}).")
            
            QMessageBox.information(self, "Sucesso", msg)
            self.set_mode(0)

        except sqlite3.IntegrityError as e:
            QMessageBox.critical(self, "Erro", f"Erro de integridade: {e}")
        except Exception as e:
            self.logger.error(f"Erro ao salvar Centro de Custo: {e}", exc_info=True)
            QMessageBox.critical(self, "Erro", f"Erro ao salvar Centro de Custo: {e}")
        finally:
            conn.close()
            
    def delete_centro_custo(self):
        if not self.current_centro_id:
            QMessageBox.warning(self, "Erro", "Nenhum centro de custo selecionado.")
            return
            
        conn = get_connection()
        try:
            cur = conn.cursor()
            
            # Verifica se está em uso
            cur.execute("SELECT id FROM titulos_financeiros WHERE centro_custo_id = ?", (self.current_centro_id,))
            titulo_usando = cur.fetchone()
            cur.execute("SELECT id FROM lancamentos_financeiros WHERE centro_custo_id = ?", (self.current_centro_id,))
            lanc_usando = cur.fetchone()
            
            if titulo_usando or lanc_usando:
                QMessageBox.critical(self, "Erro", "Não é possível excluir. Este Centro de Custo está em uso por Títulos ou Lançamentos financeiros.")
                return

            reply = QMessageBox.question(self, "Confirmação",
                f"Tem certeza que deseja excluir o Centro de Custo '{self.nome_input.text()}'?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                
            if reply == QMessageBox.No:
                return
            
            cur.execute("DELETE FROM centros_de_custo WHERE id = ?", (self.current_centro_id,))
            conn.commit()
            
            # --- LOG ADICIONADO ---
            self.logger.info(f"Usuário {self.user_id} EXCLUIU centro de custo ID {self.current_centro_id} ('{self.nome_input.text()}').")
            
            QMessageBox.information(self, "Sucesso", "Centro de Custo excluído.")
            self.set_mode(0)
            
        except Exception as e:
            self.logger.error(f"Erro ao excluir Centro de Custo: {e}", exc_info=True)
            QMessageBox.critical(self, "Erro", f"Erro ao excluir Centro de Custo: {e}")
        finally:
            conn.close()