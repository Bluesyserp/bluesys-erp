# modules/product_search_dialog.py
# (Arquivo NOVO/REESCRITO para o modelo Produto Simples)
import sqlite3
from PyQt5.QtWidgets import (
    QDialog, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, 
    QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QRadioButton, QButtonGroup,
    QSpinBox, QLabel 
)
from PyQt5.QtCore import Qt
from database.db import get_connection

class ProductSearchDialog(QDialog):
    """
    Diálogo de Busca de Produto (Modelo Simples).
    Busca em 'produtos' e 'produto_tabela_preco'.
    """
    def __init__(self, tabela_id_ativa, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Buscar Produto (F3)")
        self.setFixedSize(700, 450)
        self.setModal(True)
        
        self.tabela_id_ativa = tabela_id_ativa
        self.selected_product_id = None
        self.selected_quantity = 1
        
        self._build_ui()
        self._connect_signals()
        self.search_input.setFocus()
        
        if self.tabela_id_ativa is None:
             QMessageBox.critical(self, "Erro de Tabela", "Nenhuma tabela de preço ativa foi identificada.")
             self.setEnabled(False)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        
        # --- Controles de Busca ---
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Digite para buscar por nome ou código...")
        self.search_input.setStyleSheet("font-size: 14px; padding: 5px;")
        
        self.radio_group = QButtonGroup(self)
        self.rb_nome = QRadioButton("Por Nome/Descrição")
        self.rb_codigo = QRadioButton("Por Cód. Interno/EAN")
        self.rb_nome.setChecked(True)
        self.radio_group.addButton(self.rb_nome)
        self.radio_group.addButton(self.rb_codigo)
        
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.rb_nome)
        search_layout.addWidget(self.rb_codigo)
        layout.addLayout(search_layout)

        # --- Tabela de Resultados ---
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(["ID Produto", "Cód. Interno", "Descrição", "Preço Venda"])
        self.results_table.setColumnHidden(0, True) # Oculta ID Produto
        self.results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.results_table.setSelectionMode(QAbstractItemView.SingleSelection)
        layout.addWidget(self.results_table)

        # --- Botões de Ação ---
        btn_layout = QHBoxLayout()
        
        btn_layout.addWidget(QLabel("Quantidade:"))
        self.qty_input = QSpinBox()
        self.qty_input.setMinimum(1)
        self.qty_input.setMaximum(9999)
        self.qty_input.setFixedSize(80, 30)
        self.qty_input.setStyleSheet("font-size: 14px; padding: 5px;")
        btn_layout.addWidget(self.qty_input)
        
        btn_layout.addStretch()
        self.btn_cancelar = QPushButton("Cancelar (Esc)")
        self.btn_confirmar = QPushButton("Confirmar (Enter)")
        self.btn_confirmar.setDefault(True)
        
        btn_layout.addWidget(self.btn_cancelar)
        btn_layout.addWidget(self.btn_confirmar)
        layout.addLayout(btn_layout)
        
    def _connect_signals(self):
        self.search_input.textChanged.connect(self._search_products)
        self.rb_nome.toggled.connect(self._search_products)
        
        self.btn_confirmar.clicked.connect(self.confirm_selection)
        self.btn_cancelar.clicked.connect(self.reject)
        self.results_table.itemDoubleClicked.connect(self.confirm_selection)
        
    def _search_products(self):
        """Executa a busca no DB e preenche a tabela."""
        term = self.search_input.text().strip()
        self.results_table.setRowCount(0)
        
        if not term or self.tabela_id_ativa is None:
            return
            
        conn = get_connection()
        try:
            cur = conn.cursor()
            
            # Query base: Busca produtos ativos e junta com o Preço da Tabela Ativa
            query = """
                SELECT 
                    p.id, 
                    p.codigo_interno,
                    p.nome,
                    ptp.preco_vendadecimal
                FROM produtos p
                JOIN produto_tabela_preco ptp ON p.id = ptp.id_produto
                WHERE 
                    p.active = 1
                    AND ptp.id_tabela = ?
                    AND (
            """
            
            # Adiciona a cláusula WHERE de busca
            if self.rb_nome.isChecked():
                query += "p.nome LIKE ?)"
                search_params = [f"%{term}%"]
            else: # Cód. Interno/EAN/Alternativo
                query += "p.codigo_interno LIKE ? OR p.ean LIKE ? OR p.id IN (SELECT id_produto FROM produto_codigos_alternativos WHERE codigo LIKE ?))"
                search_params = [f"%{term}%", f"%{term}%", f"%{term}%"]
            
            query += " GROUP BY p.id ORDER BY p.nome"
            
            params = [self.tabela_id_ativa] + search_params
            cur.execute(query, tuple(params))
            
            for item in cur.fetchall():
                row = self.results_table.rowCount()
                self.results_table.insertRow(row)
                
                preco_venda = item['preco_vendadecimal'] if item['preco_vendadecimal'] is not None else 0.0
                
                self.results_table.setItem(row, 0, QTableWidgetItem(str(item['id'])))
                self.results_table.setItem(row, 1, QTableWidgetItem(item['codigo_interno']))
                self.results_table.setItem(row, 2, QTableWidgetItem(item['nome']))
                self.results_table.setItem(row, 3, QTableWidgetItem(f"R$ {preco_venda:.2f}"))
                
            if self.results_table.rowCount() > 0:
                self.results_table.selectRow(0)
                
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao buscar produtos: {e}")
        finally:
            conn.close()

    def confirm_selection(self):
        """Confirma o item selecionado e fecha o diálogo."""
        row = self.results_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Seleção", "Nenhum produto selecionado.")
            return
        
        try:
            self.selected_product_id = int(self.results_table.item(row, 0).text())
            self.selected_quantity = self.qty_input.value()
            
            preco_text = self.results_table.item(row, 3).text().replace("R$", "").replace(",", ".").strip()
            if float(preco_text) <= 0.0:
                 QMessageBox.warning(self, "Erro de Preço", "Produto sem preço de venda configurado (ou preço zero).")
                 return
                 
            self.accept()
        except ValueError:
            QMessageBox.critical(self, "Erro", "Erro ao processar a seleção. ID ou Preço inválido.")

    def get_selection(self):
        """Retorna o ID do Produto e a Quantidade."""
        return self.selected_product_id, self.selected_quantity