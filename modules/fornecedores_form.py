# -*- coding: utf-8 -*-
# modules/fornecedores_form.py
import re
import sqlite3
import requests
import json
import csv
import os
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, 
    QMessageBox, QGridLayout, QFrame, QTableWidget, QHeaderView, 
    QTableWidgetItem, QAbstractItemView, QStackedWidget, QTextEdit,
    QFileDialog
)
from PyQt5.QtCore import Qt
from database.db import get_connection

class FornecedoresForm(QWidget):
    """
    Formulário para CRUD de Fornecedores.
    """
    def __init__(self, user_id, **kwargs):
        super().__init__()
        
        # --- API TOKEN (copiado do customer_form) ---
        self.API_TOKEN = "22896|Bxa6LMJ6uAIerPz7pxBcjmKNxMCUFiZn" 
        
        self.user_id = user_id
        self.current_fornecedor_id = None
        self.setWindowTitle("Cadastro de Fornecedores")
        
        self._setup_styles()
        self._build_ui()
        self._connect_signals()
        
        self.set_mode(0) # Inicia na lista

    def _setup_styles(self):
        self.setStyleSheet("""
            QWidget { background-color: #f8f8fb; font-family: 'Segoe UI'; }
            QLabel { font-weight: bold; color: #444; }
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
            
            QLineEdit, QTextEdit {
                border: 1px solid #c0c0d0; border-radius: 5px; 
                padding: 6px; background-color: white;
            }
            QLineEdit:readOnly { background-color: #e0e0e0; }
            
            QPushButton {
                background-color: #0078d7; color: white; border-radius: 6px;
                padding: 8px 15px; font-weight: bold;
            }
            QPushButton:hover { background-color: #005fa3; }
            
            QPushButton#btn_buscar_doc {
                background-color: #2ECC71; font-size: 12px;
                padding: 6px 10px; max-width: 100px;
            }
            QPushButton#btn_buscar_doc:hover { background-color: #27AE60; }
            
            QPushButton#btn_import { background-color: #2ECC71; }
            QPushButton#btn_import:hover { background-color: #27AE60; }
            QPushButton#btn_export { background-color: #16A085; }
            QPushButton#btn_export:hover { background-color: #1ABC9C; }
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
        self.btn_novo_top = QPushButton("Novo Fornecedor")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Pesquisar por nome ou CNPJ...")
        self.btn_pesquisar = QPushButton("Pesquisar")
        
        search_layout.addWidget(self.btn_novo_top)
        search_layout.addWidget(self.search_input, 1) # Expande
        search_layout.addWidget(self.btn_pesquisar)
        
        # --- Botões de Importação/Exportação ---
        self.btn_import_csv = QPushButton("Importar CSV")
        self.btn_import_csv.setObjectName("btn_import")
        self.btn_export_csv = QPushButton("Exportar CSV")
        self.btn_export_csv.setObjectName("btn_export")
        search_layout.addSpacing(20)
        search_layout.addWidget(self.btn_import_csv)
        search_layout.addWidget(self.btn_export_csv)
        
        # --- 2. STACKED WIDGET (Tabela / Formulário) ---
        self.stack = QStackedWidget()
        
        # --- Tela 0: Tabela de Fornecedores ---
        self.table_widget = QWidget()
        table_layout = QVBoxLayout(self.table_widget)
        table_layout.setContentsMargins(0,0,0,0)
        self.fornecedor_table = QTableWidget()
        self.fornecedor_table.setColumnCount(4)
        self.fornecedor_table.setHorizontalHeaderLabels(["ID", "Nome/Razão Social", "CNPJ", "Contato"])
        self.fornecedor_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.fornecedor_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.fornecedor_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.fornecedor_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.fornecedor_table.setColumnHidden(0, True)
        table_layout.addWidget(self.fornecedor_table)
        
        # --- Tela 1: Formulário de Cadastro ---
        self.form_panel = QFrame()
        self.form_panel.setObjectName("form_panel")
        form_layout = QVBoxLayout(self.form_panel)
        self.form_title = QLabel("Cadastro de Fornecedor", objectName="form_title")
        form_layout.addWidget(self.form_title)
        
        form_grid = QGridLayout()
        form_grid.setSpacing(10)
        
        self.nome_razao_input = QLineEdit()
        self.cnpj_input = QLineEdit()
        self.cnpj_input.setInputMask("99.999.999/9999-99")
        self.btn_buscar_doc = QPushButton("Buscar Dados")
        self.btn_buscar_doc.setObjectName("btn_buscar_doc")
        self.contato_input = QTextEdit()
        self.contato_input.setPlaceholderText("Telefone, email, nome do vendedor, etc.")
        self.contato_input.setFixedHeight(80)
        
        form_grid.addWidget(QLabel("Nome/Razão Social: *", objectName="required"), 0, 0)
        form_grid.addWidget(self.nome_razao_input, 0, 1, 1, 2)
        
        form_grid.addWidget(QLabel("CNPJ:"), 1, 0)
        cnpj_layout = QHBoxLayout()
        cnpj_layout.setContentsMargins(0,0,0,0)
        cnpj_layout.addWidget(self.cnpj_input, 1)
        cnpj_layout.addWidget(self.btn_buscar_doc)
        form_grid.addLayout(cnpj_layout, 1, 1, 1, 2)
        
        form_grid.addWidget(QLabel("Informações de Contato:"), 2, 0, Qt.AlignTop)
        form_grid.addWidget(self.contato_input, 2, 1, 1, 2)
        
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
            self.load_fornecedores()
        else:
            self.stack.setCurrentIndex(1)
            self.search_panel.setVisible(False)

    def _connect_signals(self):
        self.btn_novo_top.clicked.connect(self.show_new_form)
        self.btn_salvar.clicked.connect(self.save_fornecedor)
        self.btn_excluir.clicked.connect(self.delete_fornecedor)
        self.btn_cancelar.clicked.connect(self.cancel_action)
        self.btn_pesquisar.clicked.connect(self.load_fornecedores)
        self.search_input.returnPressed.connect(self.load_fornecedores)
        self.fornecedor_table.itemDoubleClicked.connect(self._load_fornecedor_for_edit)
        self.btn_buscar_doc.clicked.connect(self.search_document)
        self.btn_import_csv.clicked.connect(self._import_csv)
        self.btn_export_csv.clicked.connect(self._export_csv)

    def _load_fornecedor_for_edit(self, item):
        """Carrega os dados de um fornecedor da tabela para o formulário."""
        row = item.row()
        fornecedor_id = int(self.fornecedor_table.item(row, 0).text())

        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM fornecedores WHERE id = ?", (fornecedor_id,))
            data = cur.fetchone()
            if not data:
                QMessageBox.critical(self, "Erro", "Fornecedor não encontrado no banco de dados.")
                return

            self.clear_form()
            self.current_fornecedor_id = fornecedor_id
            self.nome_razao_input.setText(data['nome'])
            self.cnpj_input.setText(data['cnpj'])
            self.contato_input.setText(data['contato'])

            self.form_title.setText(f"Editando Fornecedor: {data['nome']}")
            self.btn_excluir.setEnabled(True)
            self.set_mode(1) 

        except Exception as e:
            QMessageBox.critical(self, "Erro ao Carregar", f"Não foi possível carregar o fornecedor: {e}")
        finally:
            conn.close()

    def show_new_form(self):
        self.clear_form()
        self.set_mode(1)
        self.nome_razao_input.setFocus()
        self.form_title.setText("Novo Fornecedor")

    def cancel_action(self):
        self.clear_form()
        self.set_mode(0)

    def clear_form(self):
        self.current_fornecedor_id = None
        self.nome_razao_input.clear()
        self.cnpj_input.clear()
        self.contato_input.clear()
        self.nome_razao_input.setFocus()
        self.btn_excluir.setEnabled(False)
        self.form_title.setText("Cadastro de Fornecedor")

    def _validate_fields(self):
        """Verifica se os campos obrigatórios estão preenchidos."""
        if not self.nome_razao_input.text().strip(): 
            return False, "Nome/Razão Social"
        
        cnpj = self.cnpj_input.text().replace('.', '').replace('/', '').replace('-', '').strip()
        if cnpj and len(cnpj) != 14:
            return False, "CNPJ (inválido)"
            
        return True, ""

    def save_fornecedor(self):
        valido, campo = self._validate_fields()
        if not valido:
            QMessageBox.warning(self, "Campo Obrigatório", f"O campo '{campo}' é obrigatório ou inválido.")
            return

        data = {
            "nome": self.nome_razao_input.text().strip(),
            "cnpj": self.cnpj_input.text().strip() or None,
            "contato": self.contato_input.toPlainText().strip() or None,
        }

        conn = get_connection()
        try:
            cur = conn.cursor()
            
            if self.current_fornecedor_id:
                data["id"] = self.current_fornecedor_id
                query = "UPDATE fornecedores SET nome = :nome, cnpj = :cnpj, contato = :contato WHERE id = :id"
                msg = "Fornecedor atualizado com sucesso!"
                
            else:
                fields = ", ".join(data.keys())
                placeholders = ", ".join([f":{k}" for k in data.keys()])
                query = f"INSERT INTO fornecedores ({fields}) VALUES ({placeholders})"
                msg = "Fornecedor salvo com sucesso!"
            
            cur.execute(query, data)
            conn.commit()
            
            QMessageBox.information(self, "Sucesso", msg)
            self.set_mode(0)
            self.clear_form() 

        except sqlite3.IntegrityError:
             # Nota: A tabela 'fornecedores' não tem UNIQUE(cnpj) por padrão.
             # Se for adicionado, esta mensagem será útil.
            QMessageBox.critical(self, "Erro", "Este CNPJ já existe no banco de dados.")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao salvar fornecedor: {e}")
        finally:
            conn.close()
            
    def load_fornecedores(self):
        """Carrega/Busca fornecedores e preenche a tabela."""
        self.fornecedor_table.setRowCount(0)
        search_term = self.search_input.text().strip()
        
        conn = get_connection()
        try:
            cur = conn.cursor()
            query = "SELECT id, nome, cnpj, contato FROM fornecedores" 
            params = []
            
            if search_term:
                query += " WHERE (nome LIKE ? OR cnpj LIKE ?)"
                params.extend([f"%{search_term}%", f"%{search_term}%"])
            
            query += " ORDER BY nome"
            cur.execute(query, tuple(params))
            
            fornecedores = cur.fetchall()
            for f in fornecedores:
                row = self.fornecedor_table.rowCount()
                self.fornecedor_table.insertRow(row)
                self.fornecedor_table.setItem(row, 0, QTableWidgetItem(str(f['id'])))
                self.fornecedor_table.setItem(row, 1, QTableWidgetItem(f['nome']))
                self.fornecedor_table.setItem(row, 2, QTableWidgetItem(f['cnpj'] or "-"))
                
                # Limita o texto de contato para exibição na tabela
                contato_preview = (f['contato'] or "").replace("\n", " ")
                if len(contato_preview) > 70:
                    contato_preview = contato_preview[:70] + "..."
                self.fornecedor_table.setItem(row, 3, QTableWidgetItem(contato_preview))
        
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao carregar fornecedores: {e}")
        finally:
            conn.close()

    def delete_fornecedor(self):
        if not self.current_fornecedor_id:
            QMessageBox.warning(self, "Erro", "Nenhum fornecedor selecionado.")
            return

        conn = get_connection()
        try:
            cur = conn.cursor()
            # Verifica se o fornecedor está em uso na tabela 'produtos'
            cur.execute("SELECT id FROM produtos WHERE id_fornecedor = ?", (self.current_fornecedor_id,))
            produto_em_uso = cur.fetchone()
            
            if produto_em_uso:
                QMessageBox.critical(self, "Erro de Integridade", 
                    "Não é possível excluir este fornecedor, pois ele está vinculado a um ou mais produtos no 'Cadastro Básico de Produtos'.\n\n"
                    "Desvincule o fornecedor dos produtos antes de tentar excluí-lo.")
                return

            reply = QMessageBox.question(self, "Confirmação",
                f"Tem certeza que deseja excluir o fornecedor '{self.nome_razao_input.text()}'?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                
            if reply == QMessageBox.No:
                return
            
            cur.execute("DELETE FROM fornecedores WHERE id = ?", (self.current_fornecedor_id,))
            conn.commit()
            
            QMessageBox.information(self, "Sucesso", "Fornecedor excluído com sucesso.")
            self.set_mode(0)
            self.clear_form()
            
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao excluir fornecedor: {e}")
        finally:
            conn.close()

    # --- Lógica da API (Reutilizada do customer_form) ---

    def search_document(self):
        if self.API_TOKEN == "22896|Bxa6LMJ6uAIerPz7pxBcjmKNxMCUFiZn": # Exemplo, use o seu
             pass # Token OK
        else:
             QMessageBox.critical(self, "Erro de API", 
                "O Token da API 'invertexto' não foi configurado no arquivo 'fornecedores_form.py'.")
             return
            
        cnpj = self.cnpj_input.text().strip().replace(".", "").replace("/", "").replace("-", "")
        if not cnpj:
            QMessageBox.warning(self, "Campo Vazio", "Digite um CNPJ no campo 'CNPJ' para buscar os dados.")
            return
        
        self._search_cnpj(cnpj)

    def _search_cnpj(self, cnpj):
        if len(cnpj) != 14:
            QMessageBox.warning(self, "CNPJ Inválido", "O CNPJ deve conter 14 dígitos.")
            return

        try:
            url = f"https://api.invertexto.com/v1/cnpj/{cnpj}?token={self.API_TOKEN}"
            response = requests.get(url, timeout=5) 
            response.raise_for_status() 
            
            data = response.json()
            if not data or data.get("status") == "erro":
                QMessageBox.warning(self, "Erro", f"API da invertexto retornou um erro: {data.get('message', 'CNPJ não encontrado')}")
                return

            nome = data.get("razao_social", "N/A")
            fantasia = data.get("nome_fantasia", "N/A")
            
            confirm_text = (
                f"<b>Fornecedor Encontrado:</b>\n"
                f"<b>Razão Social:</b> {nome}\n"
                f"<b>Nome Fantasia:</b> {fantasia}\n\n"
                f"Deseja importar esses dados para o cadastro?"
            )
            
            reply = QMessageBox.question(self, "Confirmar Importação",
                                         confirm_text,
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)

            if reply == QMessageBox.Yes:
                self._populate_form_with_cnpj_data(data)

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                QMessageBox.warning(self, "Não Encontrado", f"O CNPJ '{cnpj}' não foi encontrado na base de dados.")
            elif e.response.status_code == 401:
                QMessageBox.critical(self, "Erro de API", "Token da API 'invertexto' é inválido ou expirou.")
            else:
                QMessageBox.critical(self, "Erro de API", f"Erro ao consultar o CNPJ: {e}")
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Erro de Rede", f"Não foi possível consultar o CNPJ (timeout?): {e}")

    def _populate_form_with_cnpj_data(self, data):
        """Preenche os campos do formulário com os dados da API."""
        
        self.nome_razao_input.setText(data.get("razao_social", ""))
        
        contato_info = []
        if data.get("telefone"):
            contato_info.append(f"Telefone: {data.get('telefone')}")
        if data.get("email"):
            contato_info.append(f"Email: {data.get('email')}")
            
        self.contato_input.setText("\n".join(contato_info))
        
        self.nome_razao_input.setFocus()
        
    # --- Lógica de Importação/Exportação CSV ---
    
    def _export_csv(self):
        """Exporta os fornecedores (nome, cnpj, contato) para CSV."""
        default_name = f"Cadastro_Fornecedores_{datetime.now():%Y%m%d}.csv"
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Exportar Cadastro de Fornecedores", default_name, "CSV Files (*.csv)"
        )
        if not save_path:
            return

        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT nome, cnpj, contato FROM fornecedores ORDER BY nome")
            rows = cur.fetchall()
            
            with open(save_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(["Nome", "CNPJ", "Contato"]) # Cabeçalho
                for row in rows:
                    writer.writerow([row['nome'], row['cnpj'], row['contato']])
            
            QMessageBox.information(self, "Sucesso", f"Fornecedores exportados para:\n{save_path}")

        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao exportar CSV: {e}")
        finally:
            conn.close()

    def _import_csv(self):
        """
        Importa um CSV no formato (Nome, CNPJ, Contato).
        Se o CNPJ já existir, atualiza; senão, insere.
        """
        save_path, _ = QFileDialog.getOpenFileName(
            self, "Importar CSV de Fornecedores", "", "CSV Files (*.csv)"
        )
        if not save_path:
            return

        conn = get_connection()
        try:
            cur = conn.cursor()
            
            # 1. Cache de CNPJs existentes
            cur.execute("SELECT cnpj, id FROM fornecedores WHERE cnpj IS NOT NULL AND cnpj != ''")
            cnpj_map = {row['cnpj']: row['id'] for row in cur.fetchall()}
            
            records_to_update = []
            records_to_insert = []
            errors = []
            
            with open(save_path, mode='r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                next(reader, None) # Pula o cabeçalho

                for i, row in enumerate(reader):
                    try:
                        nome = row[0].strip()
                        cnpj = row[1].strip()
                        contato = row[2].strip()

                        if not nome:
                            errors.append(f"Linha {i+2}: 'Nome' está vazio. Linha ignorada.")
                            continue
                            
                        # Limpa o CNPJ (se houver)
                        if cnpj:
                            cnpj = re.sub(r'[^0-9]', '', cnpj)
                            if len(cnpj) != 14:
                                cnpj = "" # Ignora CNPJ mal formatado
                            else:
                                # Formata o CNPJ para o padrão 99.999.999/9999-99
                                cnpj = f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:14]}"
                        
                        data_tuple = (nome, cnpj or None, contato or None)
                        
                        if cnpj and cnpj in cnpj_map:
                            # Adiciona ID no final para o UPDATE
                            records_to_update.append(data_tuple + (cnpj_map[cnpj],))
                        else:
                            records_to_insert.append(data_tuple)

                    except Exception as e_row:
                        errors.append(f"Linha {i+2}: Erro de formato ({e_row}). Linha ignorada.")
            
            # 5. Executa as operações no DB
            if records_to_insert:
                cur.executemany(
                    "INSERT INTO fornecedores (nome, cnpj, contato) VALUES (?, ?, ?)",
                    records_to_insert
                )
            if records_to_update:
                 cur.executemany(
                    "UPDATE fornecedores SET nome = ?, cnpj = ?, contato = ? WHERE id = ?",
                    records_to_update
                )
                 
            conn.commit()

            # 6. Exibe o resultado
            msg_final = f"{len(records_to_insert)} fornecedores criados.\n"
            msg_final += f"{len(records_to_update)} fornecedores atualizados (pelo CNPJ)."
            
            if errors:
                msg_final += f"\n\n{len(errors)} erros encontrados:\n" + "\n".join(errors[:10])
            
            QMessageBox.information(self, "Importação Concluída", msg_final)
            self.load_fornecedores() # Recarrega a tabela
            
        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Erro Fatal na Importação", f"Ocorreu um erro: {e}")
        finally:
            conn.close()