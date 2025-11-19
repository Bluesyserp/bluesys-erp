# pricing_manager.py
# -*- coding: utf-8 -*-
import sqlite3
import csv
import os 
from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, 
    QMessageBox, QGridLayout, QFrame, QTableWidget, QHeaderView, 
    QTableWidgetItem, QAbstractItemView, QStackedWidget, QComboBox,
    QTabWidget, QTextEdit, QCheckBox, QFileDialog, QDialog,
    QTextBrowser, QScrollArea # <-- Imports adicionados
)
from PyQt5.QtCore import Qt, QLocale
from PyQt5.QtGui import QDoubleValidator, QPixmap # <-- Import QPixmap adicionado
from database.db import get_connection
import datetime

class PricingManagerForm(QWidget):
    """
    Formulário Central para Gestão de Tabelas de Preço e Precificação por CNPJ.
    """
    def __init__(self, user_id, **kwargs):
        super().__init__()
        self.user_id = user_id
        self.setWindowTitle("Gestão Central de Preços (Tabela/CNPJ)")
        self.current_tabela_id = None
        
        self.tabela_map = {} # {id: nome}
        self.product_data_cache = {} # {id_produto: dados}
        
        # --- NOVO MAPA PARA O VÍNCULO ---
        self.vinculo_map = {} # {cnpj: nome_exibicao}
        
        self._setup_validators()
        self._setup_styles()
        self._build_ui()
        self._connect_signals()
        
        self._load_tabelas() 

    def _setup_validators(self):
        locale = QLocale(QLocale.Portuguese, QLocale.Brazil)
        self.price_validator = QDoubleValidator(0.00, 999999.99, 4)
        self.price_validator.setLocale(locale)
        self.price_validator.setNotation(QDoubleValidator.StandardNotation)
        
    def _setup_styles(self):
        self.setStyleSheet("""
            QWidget { background-color: #f8f8fb; font-family: 'Segoe UI'; }
            QLabel { font-weight: bold; color: #444; font-size: 13px; }
            QLabel.required::after { content: " *"; color: #e74c3c; }
            QTabWidget::pane { border-top: 1px solid #c0c0d0; background: #fdfdfd; }
            QTabBar::tab { background: #e0e0e0; padding: 8px 20px; }
            QTabBar::tab:selected { background: #fdfdfd; border: 1px solid #c0c0d0; border-bottom: none; }
            QTableWidget { border: 1px solid #c0c0d0; selection-background-color: #0078d7; font-size: 14px; }
            QHeaderView::section { background-color: #e8e8e8; padding: 8px; font-weight: bold; }
            
            QLineEdit, QComboBox, QTextEdit { border: 1px solid #c0c0d0; border-radius: 5px; padding: 6px; background-color: white; font-size: 13px; }
            
            QPushButton { background-color: #0078d7; color: white; border-radius: 6px; padding: 8px 15px; font-weight: bold; }
            QPushButton:hover { background-color: #005fa3; }
            QPushButton#btn_import { background-color: #2ECC71; }
            QPushButton#btn_import:hover { background-color: #27AE60; }
            
            QPushButton#btn_export { background-color: #16A085; }
            QPushButton#btn_export:hover { background-color: #1ABC9C; }
        """)

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # --- Aba 1: Gestão de Tabelas (Vínculo CNPJ) ---
        self.tab_tabela_crud = QWidget()
        self.tabs.addTab(self.tab_tabela_crud, "1. Vínculo CNPJ / Tabela")
        self._build_tab_tabela_crud()
        
        # --- Aba 2: Precificação e Importação ---
        self.tab_precificacao = QWidget()
        self.tabs.addTab(self.tab_precificacao, "2. Precificação / Importação")
        self._build_tab_precificacao()

    def _build_tab_tabela_crud(self):
        layout = QHBoxLayout(self.tab_tabela_crud)
        
        # Painel Esquerdo (Lista de Tabelas)
        left_frame = QFrame(objectName="form_panel")
        list_layout = QVBoxLayout(left_frame)
        
        list_layout.addWidget(QLabel("Tabelas de Preço Cadastradas:"))
        self.tabela_table = QTableWidget()
        self.tabela_table.setColumnCount(4)
        self.tabela_table.setHorizontalHeaderLabels(["ID", "Nome da Tabela", "CNPJ Vínculo", "Ativa"])
        self.tabela_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tabela_table.setColumnHidden(0, True)
        self.tabela_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabela_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        list_layout.addWidget(self.tabela_table)
        
        btn_layout = QHBoxLayout()
        self.btn_nova_tabela = QPushButton("Nova Tabela")
        self.btn_editar_tabela = QPushButton("Editar Selecionada")
        self.btn_excluir_tabela = QPushButton("Excluir Tabela")
        self.btn_excluir_tabela.setObjectName("deleteButton")
        btn_layout.addWidget(self.btn_nova_tabela)
        btn_layout.addWidget(self.btn_editar_tabela)
        btn_layout.addWidget(self.btn_excluir_tabela)
        list_layout.addLayout(btn_layout)
        layout.addWidget(left_frame, 1)

        # Painel Direito (Edição/Formulário)
        self.form_tabela_frame = QFrame(objectName="form_panel")
        self.form_tabela_frame.setEnabled(False) # Começa desabilitado
        form_layout = QVBoxLayout(self.form_tabela_frame)
        self.tabela_form_title = QLabel("Detalhes da Tabela de Preço", objectName="form_title")
        form_layout.addWidget(self.tabela_form_title)
        
        grid = QGridLayout()
        self.nome_tabela_input = QLineEdit()
        
        self.cnpj_vinculo_combo = QComboBox()
        
        self.descricao_input = QTextEdit()
        self.ativo_check = QCheckBox("Tabela Ativa")
        self.ativo_check.setChecked(True)
        
        grid.addWidget(QLabel("Nome da Tabela: *", objectName="required"), 0, 0)
        grid.addWidget(self.nome_tabela_input, 0, 1)
        
        grid.addWidget(QLabel("Vincular ao CNPJ (Empresa/Local): *", objectName="required"), 1, 0)
        grid.addWidget(self.cnpj_vinculo_combo, 1, 1)
        
        grid.addWidget(QLabel("Descrição:"), 2, 0, Qt.AlignTop)
        grid.addWidget(self.descricao_input, 2, 1)
        grid.addWidget(self.ativo_check, 3, 1)
        
        form_layout.addLayout(grid)
        form_layout.addStretch()

        btn_action_layout = QHBoxLayout()
        btn_action_layout.addStretch()
        self.btn_cancelar_tabela = QPushButton("Cancelar")
        self.btn_salvar_tabela = QPushButton("Salvar Tabela")
        btn_action_layout.addWidget(self.btn_cancelar_tabela)
        btn_action_layout.addWidget(self.btn_salvar_tabela)
        form_layout.addLayout(btn_action_layout)
        
        layout.addWidget(self.form_tabela_frame, 1)

    def _build_tab_precificacao(self):
        layout = QVBoxLayout(self.tab_precificacao)
        
        # Painel de Seleção e Ações
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Tabela de Preço Selecionada:", objectName="required"))
        self.pricing_tabela_combo = QComboBox()
        header_layout.addWidget(self.pricing_tabela_combo, 1)
        
        self.btn_import_csv = QPushButton("Importar CSV de Preços")
        self.btn_import_csv.setObjectName("btn_import")
        
        # --- BOTÃO DE AJUDA ADICIONADO ---
        self.btn_import_help = QPushButton("❓")
        self.btn_import_help.setToolTip("Ajuda sobre o formato de importação CSV")
        self.btn_import_help.setFixedSize(35, 35)
        self.btn_import_help.setStyleSheet("font-size: 16px; background-color: #95A5A6; color: white; padding: 8px;")
        
        self.btn_export_csv = QPushButton("Exportar Tabela Atual")
        self.btn_export_csv.setObjectName("btn_export")
        
        header_layout.addWidget(self.btn_import_csv)
        header_layout.addWidget(self.btn_import_help) # Botão adicionado
        header_layout.addWidget(self.btn_export_csv)
        layout.addLayout(header_layout)
        
        # Grid de Precificação
        self.pricing_grid = QTableWidget()
        self.pricing_grid.setColumnCount(6)
        self.pricing_grid.setHorizontalHeaderLabels(["ID Produto", "Cód. Interno", "Nome do Produto", "Preço Venda (R$)", "Preço Custo (R$)", "Margem (%)"])
        self.pricing_grid.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.pricing_grid.setColumnHidden(0, True)
        self.pricing_grid.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.pricing_grid.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.AnyKeyPressed)
        layout.addWidget(self.pricing_grid, 1)
        
        # Botão de Salvar Grid
        self.btn_salvar_grid = QPushButton("Salvar Alterações da Tabela")
        self.btn_salvar_grid.setStyleSheet("background-color: #0078d7;")
        self.btn_salvar_grid.setEnabled(False)
        layout.addWidget(self.btn_salvar_grid)

    def _connect_signals(self):
        # CRUD de Tabelas
        self.tabela_table.itemDoubleClicked.connect(self._load_tabela_for_edit)
        self.btn_nova_tabela.clicked.connect(lambda: self._set_tabela_crud_mode(None))
        self.btn_editar_tabela.clicked.connect(self._edit_selected_tabela)
        self.btn_salvar_tabela.clicked.connect(self._save_tabela)
        self.btn_cancelar_tabela.clicked.connect(lambda: self._set_tabela_crud_mode(False))
        self.btn_excluir_tabela.clicked.connect(self._delete_tabela)
        
        # Precificação
        self.pricing_tabela_combo.currentIndexChanged.connect(self._load_pricing_grid)
        self.btn_salvar_grid.clicked.connect(self._save_pricing_grid)
        self.pricing_grid.cellChanged.connect(self._on_price_or_cost_changed)
        
        # Import/Export
        self.btn_import_csv.clicked.connect(self._import_csv)
        self.btn_export_csv.clicked.connect(self._export_csv)
        
        # --- NOVA CONEXÃO ---
        self.btn_import_help.clicked.connect(self._show_import_help)

    # --- LÓGICA DE TABELA DE PREÇOS (CRUD) ---

    def _load_tabelas(self):
        # (Inalterado)
        self.tabela_table.setRowCount(0)
        self.tabela_map.clear()
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, nome_tabela, identificador_loja, active FROM tabelas_preco ORDER BY nome_tabela")
            tabelas = cur.fetchall()
            
            self.pricing_tabela_combo.clear()
            self.pricing_tabela_combo.addItem("Selecione uma Tabela...", None)

            for tab in tabelas:
                row = self.tabela_table.rowCount()
                self.tabela_table.insertRow(row)
                
                status_text = "Sim" if tab['active'] else "Não"
                self.tabela_table.setItem(row, 0, QTableWidgetItem(str(tab['id'])))
                self.tabela_table.setItem(row, 1, QTableWidgetItem(tab['nome_tabela']))
                self.tabela_table.setItem(row, 2, QTableWidgetItem(tab['identificador_loja']))
                self.tabela_table.setItem(row, 3, QTableWidgetItem(status_text))
                
                self.pricing_tabela_combo.addItem(f"{tab['nome_tabela']} ({tab['identificador_loja']})", tab['id'])
                self.tabela_map[tab['id']] = tab['nome_tabela']

            self.btn_editar_tabela.setEnabled(False)
            self.btn_excluir_tabela.setEnabled(False)
        except Exception as e:
            QMessageBox.critical(self, "Erro DB", f"Erro ao carregar tabelas de preço: {e}")
        finally:
            conn.close()

    def _load_tabela_for_edit(self, item):
        # (Inalterado)
        row = item.row()
        tabela_id = int(self.tabela_table.item(row, 0).text())
        self._set_tabela_crud_mode(tabela_id)

    def _set_tabela_crud_mode(self, tabela_id=None):
        # (Inalterado)
        if tabela_id is None:
            # --- MODO NOVO ---
            self.current_tabela_id = None
            self.tabela_form_title.setText("Nova Tabela de Preço")
            self._load_vinculo_combobox() # Carrega o combo de CNPJs
            self.nome_tabela_input.clear()
            self.cnpj_vinculo_combo.setCurrentIndex(0) # Reseta o combo
            self.descricao_input.clear()
            self.ativo_check.setChecked(True)
            self.form_tabela_frame.setEnabled(True)
            self.tabela_table.clearSelection()
            
        elif tabela_id is not False:
            # --- MODO EDIÇÃO ---
            self._load_vinculo_combobox() # Carrega o combo de CNPJs
            conn = get_connection()
            try:
                cur = conn.cursor()
                cur.execute("SELECT * FROM tabelas_preco WHERE id = ?", (tabela_id,))
                data = cur.fetchone()
                if not data: return
                self.current_tabela_id = data['id']
                self.tabela_form_title.setText(f"Editando: {data['nome_tabela']}")
                self.nome_tabela_input.setText(data['nome_tabela'])
                self.descricao_input.setText(data['descricao'])
                self.ativo_check.setChecked(bool(data['active']))
                
                cnpj_salvo = data['identificador_loja']
                index = self.cnpj_vinculo_combo.findData(cnpj_salvo)
                if index > -1:
                    self.cnpj_vinculo_combo.setCurrentIndex(index)
                elif cnpj_salvo:
                    self.cnpj_vinculo_combo.addItem(f"[VÍNCULO ANTIGO] ({cnpj_salvo})", cnpj_salvo)
                    self.cnpj_vinculo_combo.setCurrentIndex(self.cnpj_vinculo_combo.count() - 1)
                
                self.form_tabela_frame.setEnabled(True)
            finally:
                conn.close()
        else:
            # --- MODO DESABILITADO ---
            self.current_tabela_id = None
            self.tabela_form_title.setText("Detalhes da Tabela de Preço")
            self.form_tabela_frame.setEnabled(False)
            self.tabela_table.clearSelection()

    def _edit_selected_tabela(self):
        # (Inalterado)
        selected = self.tabela_table.selectedItems()
        if selected:
            tabela_id = int(self.tabela_table.item(selected[0].row(), 0).text())
            self._set_tabela_crud_mode(tabela_id)
        else:
             QMessageBox.warning(self, "Seleção", "Selecione uma tabela para editar.")

    def _save_tabela(self):
        # (Inalterado)
        nome = self.nome_tabela_input.text().strip()
        cnpj = self.cnpj_vinculo_combo.currentData()
        
        if not nome or not cnpj:
            QMessageBox.warning(self, "Erro", "Nome da tabela e Vínculo de CNPJ são obrigatórios.")
            return

        data = {
            "nome_tabela": nome,
            "identificador_loja": cnpj, # Salva o CNPJ selecionado
            "descricao": self.descricao_input.toPlainText().strip() or None,
            "active": 1 if self.ativo_check.isChecked() else 0
        }
        
        conn = get_connection()
        try:
            cur = conn.cursor()
            if self.current_tabela_id:
                data["id"] = self.current_tabela_id
                fields_to_update = [f"{key} = :{key}" for key in data.keys() if key != 'id']
                query = f"UPDATE tabelas_preco SET {', '.join(fields_to_update)} WHERE id = :id"
            else:
                fields = ", ".join(data.keys())
                placeholders = ", ".join([f":{k}" for k in data.keys()])
                query = f"INSERT INTO tabelas_preco ({fields}) VALUES ({placeholders})"
            
            cur.execute(query, data)
            conn.commit()
            QMessageBox.information(self, "Sucesso", "Tabela salva com sucesso.")
            self._load_tabelas()
            self._set_tabela_crud_mode(False)
        except sqlite3.IntegrityError:
            QMessageBox.critical(self, "Erro", "Já existe uma tabela com o mesmo nome para este CNPJ.")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao salvar tabela: {e}")
        finally:
            conn.close()

    def _delete_tabela(self):
        # (Inalterado)
        selected = self.tabela_table.selectedItems()
        if not selected: 
             QMessageBox.warning(self, "Seleção", "Selecione uma tabela para excluir.")
             return
             
        tabela_id = int(self.tabela_table.item(selected[0].row(), 0).text())
        tabela_nome = self.tabela_table.item(selected[0].row(), 1).text()

        reply = QMessageBox.question(self, "Confirmação",
            f"Tem certeza que deseja excluir a tabela '{tabela_nome}'?\n"
            "Todos os preços associados serão removidos.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            
        if reply == QMessageBox.Yes:
            conn = get_connection()
            try:
                cur = conn.cursor()
                cur.execute("DELETE FROM tabelas_preco WHERE id = ?", (tabela_id,))
                conn.commit()
                QMessageBox.information(self, "Sucesso", "Tabela excluída.")
                self._load_tabelas()
                self._set_tabela_crud_mode(False)
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Erro ao excluir: {e}")
            finally:
                conn.close()

    # --- FUNÇÃO (Inalterada) ---
    def _load_vinculo_combobox(self):
        """
        Carrega o ComboBox com todos os CNPJs válidos (de Empresas e Locais).
        """
        self.cnpj_vinculo_combo.clear()
        self.vinculo_map.clear()
        
        conn = get_connection()
        try:
            cur = conn.cursor()
            
            # 1. Busca Empresas
            cur.execute("SELECT id, razao_social, cnpj FROM empresas WHERE status = 1")
            empresas = cur.fetchall()
            
            empresa_cnpjs = {} # Cache de CNPJ da empresa por ID
            
            self.cnpj_vinculo_combo.addItem("Selecione um Vínculo (Empresa ou Local)...", None)
            
            for emp in empresas:
                cnpj = emp['cnpj']
                empresa_cnpjs[emp['id']] = cnpj
                if cnpj not in self.vinculo_map:
                    nome = f"[MATRIZ] {emp['razao_social']} ({cnpj})"
                    self.cnpj_vinculo_combo.addItem(nome, cnpj)
                    self.vinculo_map[cnpj] = nome
                    
            # 2. Busca Locais
            cur.execute("SELECT id, nome_local, cnpj, empresa_id FROM locais_escrituracao WHERE status = 1")
            locais = cur.fetchall()
            
            for loc in locais:
                empresa_cnpj_fallback = empresa_cnpjs.get(loc['empresa_id'], None)
                
                # O CNPJ a ser usado é o do local, ou (se não tiver) o da matriz
                cnpj_a_usar = loc['cnpj'] if loc['cnpj'] else empresa_cnpj_fallback
                
                if not cnpj_a_usar:
                    continue # Local não tem CNPJ e sua matriz também não (raro)
                    
                # Só adiciona se o CNPJ for diferente dos que já estão na lista
                if cnpj_a_usar not in self.vinculo_map:
                    nome = f"[LOCAL] {loc['nome_local']} ({cnpj_a_usar})"
                    self.cnpj_vinculo_combo.addItem(nome, cnpj_a_usar)
                    self.vinculo_map[cnpj_a_usar] = nome
                    
        except Exception as e:
            QMessageBox.critical(self, "Erro DB", f"Erro ao carregar vínculos de CNPJ: {e}")
        finally:
            if conn:
                conn.close()

    # --- LÓGICA DE PRECIFICAÇÃO (GRID) ---
    
    def _load_pricing_grid(self):
        # (Inalterado)
        self.pricing_grid.setRowCount(0)
        self.product_data_cache.clear()
        self.btn_salvar_grid.setEnabled(False)
        
        tabela_id = self.pricing_tabela_combo.currentData()
        if tabela_id is None: return

        conn = get_connection()
        try:
            # 1. Busca todos os produtos mestre (simples)
            cur = conn.cursor()
            cur.execute("SELECT id, nome, codigo_interno FROM produtos WHERE active = 1 ORDER BY nome")
            products = cur.fetchall()
            
            # 2. Busca os preços existentes para esta tabela
            cur.execute("""
                SELECT id_produto, preco_vendadecimal, preco_custodecimal, margemdecimal
                FROM produto_tabela_preco 
                WHERE id_tabela = ?
            """, (tabela_id,))
            pricing = {p['id_produto']: p for p in cur.fetchall()}
            
            for prod in products:
                prod_id = prod['id']
                pricing_data = pricing.get(prod_id, {})
                
                venda = pricing_data.get('preco_vendadecimal', 0.0)
                custo = pricing_data.get('preco_custodecimal', 0.0)
                margem = pricing_data.get('margemdecimal', 0.0)
                
                self.product_data_cache[prod_id] = {'id': prod_id, 'venda': venda, 'custo': custo, 'margem': margem}
                
                row = self.pricing_grid.rowCount()
                self.pricing_grid.insertRow(row)
                
                self.pricing_grid.setItem(row, 0, QTableWidgetItem(str(prod_id)))
                self.pricing_grid.setItem(row, 1, QTableWidgetItem(prod['codigo_interno']))
                self.pricing_grid.setItem(row, 2, QTableWidgetItem(prod['nome']))
                
                self._set_numeric_item(row, 3, venda)
                self._set_numeric_item(row, 4, custo)
                
                margem_item = QTableWidgetItem(f"{margem:.2f}")
                margem_item.setFlags(margem_item.flags() & ~Qt.ItemIsEditable) 
                self.pricing_grid.setItem(row, 5, margem_item)
            
            self.btn_salvar_grid.setEnabled(True)

        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao carregar grid de precificação: {e}")
        finally:
            conn.close()

    def _set_numeric_item(self, row, col, value):
        # (Inalterado)
        item = QTableWidgetItem(f"{value:.2f}".replace('.', ','))
        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        item.setToolTip("Duplo clique para editar")
        self.pricing_grid.setItem(row, col, item)

    def _on_price_or_cost_changed(self, row, col):
        # (Inalterado)
        if col not in [3, 4]: return 
        
        try:
            self.pricing_grid.cellChanged.disconnect(self._on_price_or_cost_changed)
            
            venda_str = self.pricing_grid.item(row, 3).text().replace(',', '.')
            custo_str = self.pricing_grid.item(row, 4).text().replace(',', '.')
            
            venda = float(venda_str)
            custo = float(custo_str)
            
            margem = 0.0
            if custo > 0:
                margem = ((venda - custo) / custo) * 100.0
            elif venda > 0 and custo == 0:
                 margem = 100.0 
                 
            self.pricing_grid.item(row, 5).setText(f"{min(margem, 999.99):.2f}")
            
            self.pricing_grid.cellChanged.connect(self._on_price_or_cost_changed)
            
        except Exception:
             self.pricing_grid.cellChanged.connect(self._on_price_or_cost_changed)
             pass 

    def _save_pricing_grid(self):
        # (Inalterado)
        tabela_id = self.pricing_tabela_combo.currentData()
        if tabela_id is None:
            QMessageBox.warning(self, "Erro", "Selecione uma tabela para salvar.")
            return
        
        conn = get_connection()
        cursor = conn.cursor()
        
        records_to_save = []
        try:
            for row in range(self.pricing_grid.rowCount()):
                prod_id = int(self.pricing_grid.item(row, 0).text())
                
                venda = float(self.pricing_grid.item(row, 3).text().replace(',', '.'))
                custo = float(self.pricing_grid.item(row, 4).text().replace(',', '.'))
                margem = float(self.pricing_grid.item(row, 5).text().replace(',', '.'))
                
                records_to_save.append({
                    "id_produto": prod_id,
                    "id_tabela": tabela_id,
                    "preco_vendadecimal": venda, 
                    "preco_custodecimal": custo,
                    "margemdecimal": margem
                })
            
            cursor.executemany("""
                INSERT INTO produto_tabela_preco 
                (id_produto, id_tabela, preco_vendadecimal, preco_custodecimal, margemdecimal, data_ultima_atualizacao)
                VALUES (:id_produto, :id_tabela, :preco_vendadecimal, :preco_custodecimal, :margemdecimal, CURRENT_TIMESTAMP)
                ON CONFLICT(id_produto, id_tabela) DO UPDATE SET
                    preco_vendadecimal = excluded.preco_vendadecimal,
                    preco_custodecimal = excluded.preco_custodecimal,
                    margemdecimal = excluded.margemdecimal,
                    data_ultima_atualizacao = excluded.data_ultima_atualizacao
            """, records_to_save)
            
            conn.commit()
            QMessageBox.information(self, "Sucesso", f"Preços atualizados para a Tabela ID {tabela_id}!")

        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Erro ao Salvar", f"Falha ao salvar a grade de preços: {e}")
        finally:
            conn.close()

    # --- LÓGICA DE IMPORTAÇÃO/EXPORTAÇÃO (Req #8) ---
    def _import_csv(self):
        # (Inalterado)
        save_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Importar CSV de Preços", 
            "", 
            "CSV Files (*.csv)"
        )
        
        if not save_path:
            return

        conn = get_connection()
        try:
            cur = conn.cursor()
            
            # Cache de produtos e tabelas para otimização
            cur.execute("SELECT codigo_interno, id FROM produtos")
            product_map = {row['codigo_interno']: row['id'] for row in cur.fetchall()}
            
            cur.execute("SELECT (identificador_loja || nome_tabela) as chave, id FROM tabelas_preco")
            tabela_map = {row['chave']: row['id'] for row in cur.fetchall()}
            
            records_to_upsert = [] 
            errors = []
            
            with open(save_path, mode='r', encoding='utf-8-sig') as f: # utf-8-sig lida com BOM
                reader = csv.reader(f)
                next(reader, None) # Pula o cabeçalho

                for i, row in enumerate(reader):
                    try:
                        # 1. Extrai dados (CNPJ,Nome Tabela,Cód Produto,Preço Venda,Preço Custo)
                        cnpj = row[0].strip()
                        nome_tabela = row[1].strip()
                        cod_produto = row[2].strip()
                        preco_venda = float(row[3].replace(',', '.'))
                        preco_custo = float(row[4].replace(',', '.'))
                        
                        # 2. Encontra ou Cria a Tabela de Preço
                        tabela_key = f"{cnpj}{nome_tabela}"
                        tabela_id = tabela_map.get(tabela_key)
                        
                        if tabela_id is None:
                            # Cria a tabela se não existir
                            cur.execute("""
                                INSERT INTO tabelas_preco (nome_tabela, identificador_loja, active) 
                                VALUES (?, ?, 1)
                            """, (nome_tabela, cnpj))
                            tabela_id = cur.lastrowid
                            tabela_map[tabela_key] = tabela_id # Atualiza o cache
                            
                        # 3. Encontra o Produto
                        id_produto = product_map.get(cod_produto)
                        if id_produto is None:
                            errors.append(f"Linha {i+2}: Produto com Cód. Interno '{cod_produto}' não encontrado.")
                            continue
                            
                        # 4. Calcula a Margem
                        margem = 0.0
                        if preco_custo > 0:
                            margem = ((preco_venda - preco_custo) / preco_custo) * 100.0
                        elif preco_venda > 0:
                            margem = 100.0
                            
                        records_to_upsert.append(( 
                            id_produto, tabela_id, preco_venda, preco_custo, margem
                        ))

                    except Exception as e_row:
                        errors.append(f"Linha {i+2}: Erro de formato ou dados inválidos ({e_row}).")
            
            # 5. Executa o UPSERT em massa
            if records_to_upsert:
                cur.executemany("""
                    INSERT INTO produto_tabela_preco 
                    (id_produto, id_tabela, preco_vendadecimal, preco_custodecimal, margemdecimal, data_ultima_atualizacao)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(id_produto, id_tabela) DO UPDATE SET
                        preco_vendadecimal = excluded.preco_vendadecimal,
                        preco_custodecimal = excluded.preco_custodecimal,
                        margemdecimal = excluded.margemdecimal,
                        data_ultima_atualizacao = excluded.data_ultima_atualizacao
                """, records_to_upsert) 
                conn.commit()

            # 6. Exibe o resultado
            msg_final = f"{len(records_to_upsert)} preços importados/atualizados com sucesso."
            if errors:
                msg_final += f"\n\n{len(errors)} erros encontrados:\n" + "\n".join(errors[:10]) # Limita a 10 erros
            
            QMessageBox.information(self, "Importação Concluída", msg_final)
            self._load_tabelas() # Atualiza a lista de tabelas (caso novas tenham sido criadas)
            self._load_pricing_grid() # Recarrega a grid
            
        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Erro Fatal na Importação", f"Ocorreu um erro: {e}")
        finally:
            conn.close()

    def _export_csv(self):
        # (Inalterado)
        tabela_id = self.pricing_tabela_combo.currentData()
        if tabela_id is None:
            QMessageBox.warning(self, "Erro", "Selecione uma tabela para exportar.")
            return

        default_name = f"Tabela_{self.pricing_tabela_combo.currentText().split(' ')[0]}_{datetime.now():%Y%m%d}.csv"
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Exportar Tabela CSV", default_name, "CSV Files (*.csv)"
        )
        if not save_path:
            return

        conn = get_connection()
        try:
            cur = conn.cursor()
            # Busca os dados da tabela selecionada
            cur.execute("""
                SELECT 
                    t.identificador_loja, 
                    t.nome_tabela, 
                    p.codigo_interno, 
                    ptp.preco_vendadecimal, 
                    ptp.preco_custodecimal
                FROM produto_tabela_preco ptp
                JOIN produtos p ON p.id = ptp.id_produto
                JOIN tabelas_preco t ON t.id = ptp.id_tabela
                WHERE ptp.id_tabela = ?
            """, (tabela_id,))
            
            rows = cur.fetchall()
            
            with open(save_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # Cabeçalho
                writer.writerow(["CNPJ", "Nome da Tabela", "Código Produto", "Preço Venda", "Preço Custo"])
                # Dados
                for row in rows:
                    writer.writerow([
                        row['identificador_loja'], 
                        row['nome_tabela'], 
                        row['codigo_interno'],
                        f"{row['preco_vendadecimal']:.2f}".replace('.', ','),
                        f"{row['preco_custodecimal']:.2f}".replace('.', ',')
                    ])
            
            QMessageBox.information(self, "Sucesso", f"Tabela exportada para:\n{save_path}")

        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao exportar CSV: {e}")
        finally:
            conn.close()
            
    # --- NOVA FUNÇÃO DE AJUDA ---
    def _show_import_help(self):
        """
        Exibe um diálogo modal com instruções e uma imagem de exemplo
        para a importação de PREÇOS.
        """
        dialog = QDialog(self)
        dialog.setWindowTitle("Ajuda - Importação de Preços via CSV")
        dialog.setFixedSize(700, 600)
        dialog.setModal(True)
        
        layout = QVBoxLayout(dialog)
        
        # Texto de ajuda (HTML)
        help_text = """
        <h2>Formato de Importação de Preços (.csv UTF-8)</h2>
        <p>Este importador atualiza (ou cria) tabelas de preço em massa.</p>
        
        <h3>Colunas Obrigatórias:</h3>
        <ol>
            <li><b>CNPJ</b>: O CNPJ da Empresa/Local ao qual esta tabela pertence.</li>
            <li><b>Nome Tabela</b>: O nome da tabela de preço (Ex: "Tabela Varejo").</li>
            <li><b>Código Produto</b>: O <b>codigo_interno</b> (SKU) do produto.</li>
            <li><b>Preço Venda</b>: O preço final (use <b>vírgula</b> decimal, ex: <code>19,90</code>).</li>
            <li><b>Preço Custo</b>: O preço de custo (use <b>vírgula</b> decimal, ex: <code>10,00</code>).</li>
        </ol>

        <h3>Como Funciona:</h3>
        <ul>
            <li><b>Tabelas de Preço:</b> Se a combinação <code>CNPJ + Nome Tabela</code> não existir, uma nova tabela de preço será <b>criada</b>.</li>
            <li><b>Produtos:</b> O <code>Código Produto</code> (codigo_interno) <b>deve existir</b> no Cadastro de Produtos. Linhas com códigos não encontrados serão ignoradas.</li>
            <li><b>Atualização:</b> O sistema irá <b>inserir ou atualizar</b> o preço (venda e custo) do produto para a tabela de preço especificada.</li>
        </ul>
        
        <h3>Exemplo de Imagem (Layout):</h3>
        """
        
        text_browser = QTextBrowser()
        text_browser.setHtml(help_text)
        text_browser.setOpenExternalLinks(True)
        text_browser.setFixedHeight(300)
        layout.addWidget(text_browser)

        # Imagem
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        image_label = QLabel("Imagem de exemplo não encontrada.")
        image_label.setAlignment(Qt.AlignCenter)
        
        # Define o caminho da imagem de exemplo
        image_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "exemplo_import_preco.png"))

        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            image_label.setPixmap(pixmap.scaled(650, 250, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            image_label.setText(f"<b>Imagem de exemplo não encontrada.</b>\n\n(Coloque o arquivo 'exemplo_import_preco.png' na pasta 'assets' do sistema)")
            image_label.setStyleSheet("color: #c0392b; font-size: 14px;")

        scroll_area.setWidget(image_label)
        layout.addWidget(scroll_area)
        
        # Botão OK
        btn_ok = QPushButton("OK")
        btn_ok.clicked.connect(dialog.accept)
        layout.addWidget(btn_ok, 0, Qt.AlignRight)
        
        dialog.exec_()