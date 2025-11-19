# modules/relatorio_vendas_produto.py
import sqlite3
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, 
    QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView, 
    QAbstractItemView, QDateEdit, QCalendarWidget, QComboBox,
    QFrame, QLineEdit, QGridLayout, QFileDialog
)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, QDate
from database.db import get_connection
from .report_exporter import export_to_pdf, export_to_xlsx

class RelatorioVendasProduto(QWidget):
    """
    Relatório de Vendas por Produto (Analítico de Itens).
    """
    def __init__(self, user_id, **kwargs):
        super().__init__()
        self.user_id = user_id
        self.setWindowTitle("Relatório de Vendas por Produto")
        
        self._setup_styles()
        self._build_ui()
        self._connect_signals()
        
        self.load_report(show_message=False) 

    def _setup_styles(self):
        # (CSS Inalterado)
        self.setStyleSheet("""
            QWidget { background-color: #f8f8fb; font-family: 'Segoe UI'; }
            QLabel { font-weight: bold; color: #444; }
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
            QDateEdit, QComboBox, QLineEdit {
                border: 1px solid #c0c0d0; border-radius: 5px; 
                padding: 6px; background-color: white;
            }
            QCalendarWidget QWidget { 
                background-color: #f0f0f0; 
                font-size: 10px; 
            }
            QCalendarWidget QToolButton { 
                background-color: #e0e0e0; 
                color: #333; 
            }
            QPushButton {
                background-color: #0078d7; color: white; border-radius: 6px;
                padding: 8px 15px; font-weight: bold;
            }
            QPushButton:hover { background-color: #005fa3; }
            
            QPushButton#btn_export_pdf { background-color: #c0392b; }
            QPushButton#btn_export_pdf:hover { background-color: #e74c3c; }
            QPushButton#btn_export_xlsx { background-color: #16A085; }
            QPushButton#btn_export_xlsx:hover { background-color: #1ABC9C; }
            QFrame#filter_frame {
                background-color: #fdfdfd;
                border: 1px solid #c0c0d0;
                border-radius: 8px;
            }
        """)

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        
        filter_frame = QFrame()
        filter_frame.setObjectName("filter_frame")
        filter_layout = QGridLayout(filter_frame)
        filter_layout.setContentsMargins(10, 10, 10, 10)
        filter_layout.setSpacing(10)
        
        filter_layout.addWidget(QLabel("Data Início:"), 0, 0)
        self.date_start = QDateEdit()
        self.date_start.setDate(QDate.currentDate())
        self.date_start.setCalendarPopup(True)
        filter_layout.addWidget(self.date_start, 0, 1)
        
        filter_layout.addWidget(QLabel("Data Fim:"), 0, 2)
        self.date_end = QDateEdit()
        self.date_end.setDate(QDate.currentDate())
        self.date_end.setCalendarPopup(True)
        filter_layout.addWidget(self.date_end, 0, 3)
        
        filter_layout.addWidget(QLabel("Empresa:"), 1, 0)
        self.empresa_combo = QComboBox()
        filter_layout.addWidget(self.empresa_combo, 1, 1, 1, 3) 
        
        filter_layout.addWidget(QLabel("Terminal:"), 2, 0)
        self.terminal_combo = QComboBox()
        filter_layout.addWidget(self.terminal_combo, 2, 1)
        
        filter_layout.addWidget(QLabel("Cód. Produto:"), 2, 2)
        self.produto_input = QLineEdit()
        # --- CORREÇÃO: Placeholder para refletir a busca por SKU/EAN ---
        self.produto_input.setPlaceholderText("Cód. Barras (EAN) ou Cód. Interno (SKU)...")
        filter_layout.addWidget(self.produto_input, 2, 3)

        self.btn_filtrar = QPushButton("Filtrar")
        filter_layout.addWidget(self.btn_filtrar, 2, 4)
        
        export_layout = QHBoxLayout()
        self.btn_export_pdf = QPushButton("Exportar PDF")
        self.btn_export_pdf.setObjectName("btn_export_pdf")
        self.btn_export_xlsx = QPushButton("Exportar XLSX")
        self.btn_export_xlsx.setObjectName("btn_export_xlsx")
        export_layout.addStretch()
        export_layout.addWidget(self.btn_export_pdf)
        export_layout.addWidget(self.btn_export_xlsx)
        
        self.btn_export_pdf.setEnabled(False) 
        self.btn_export_xlsx.setEnabled(False)

        filter_layout.addLayout(export_layout, 2, 5, 1, 2)
        filter_layout.setColumnStretch(6, 1) 
        
        main_layout.addWidget(filter_frame)

        self.report_table = QTableWidget()
        self.report_table.setColumnCount(7)
        self.report_table.setHorizontalHeaderLabels([
            "Data/Hora", "Nº Venda", "Código", "Descrição", 
            "Qtd.", "Vl. Unit.", "Vl. Total"
        ])
        self.report_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.report_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.report_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.report_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        
        main_layout.addWidget(self.report_table)
        
        self._load_filters()

    def _load_filters(self):
        conn = get_connection()
        try:
            cur_emp = conn.cursor()
            cur_emp.execute("SELECT id, razao_social FROM empresas WHERE status = 1 ORDER BY razao_social")
            self.empresa_combo.addItem("Todas as Empresas", None)
            for emp in cur_emp.fetchall():
                self.empresa_combo.addItem(emp['razao_social'], emp['id'])

            cur_term = conn.cursor()
            cur_term.execute("SELECT id, nome_terminal FROM terminais_pdv ORDER BY nome_terminal")
            self.terminal_combo.addItem("Todos os Terminais", None)
            for term in cur_term.fetchall():
                self.terminal_combo.addItem(term['nome_terminal'], term['id'])
                
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao carregar filtros: {e}")
        finally:
            conn.close()

    def _connect_signals(self):
        self.btn_filtrar.clicked.connect(lambda: self.load_report(show_message=True))
        self.produto_input.returnPressed.connect(lambda: self.load_report(show_message=True))
        
        self.btn_export_pdf.clicked.connect(self._export_pdf)
        self.btn_export_xlsx.clicked.connect(self._export_xlsx)

    def load_report(self, show_message=False):
        """Carrega os dados do relatório com base nos filtros."""
        self.report_table.setRowCount(0)
        
        date_start_str = self.date_start.date().toString("yyyy-MM-dd") + " 00:00:00"
        date_end_str = self.date_end.date().toString("yyyy-MM-dd") + " 23:59:59"
        empresa_id = self.empresa_combo.currentData()
        terminal_id = self.terminal_combo.currentData()
        produto_codigo = self.produto_input.text().strip()
        
        conn = get_connection()
        try:
            cur = conn.cursor()
            
            # A query usa vendas_itens (histórico) que contém o código do SKU vendido.
            query = """
                SELECT 
                    v.data_venda, v.numero_venda_terminal,
                    vi.codigo_barras, vi.descricao,
                    vi.quantidade, vi.preco_unitario, vi.total_item
                FROM vendas_itens vi
                JOIN vendas v ON vi.venda_id = v.id
                WHERE v.data_venda BETWEEN ? AND ?
                  AND v.status = 'FINALIZADA'
            """
            params = [date_start_str, date_end_str]
            
            if empresa_id:
                query += " AND v.empresa_id = ?"
                params.append(empresa_id)
            if terminal_id:
                query += " AND v.terminal_id = ?"
                params.append(terminal_id)
                
            # --- CORREÇÃO: Filtro de Código (ignora case, busca LIKE) ---
            if produto_codigo:
                # Busca por código de barras (EAN) ou código interno (SKU)
                query += " AND vi.codigo_barras LIKE ?"
                params.append(f"%{produto_codigo}%")
                
            query += " ORDER BY v.data_venda DESC, v.numero_venda_terminal DESC"
            
            cur.execute(query, tuple(params))
            itens = cur.fetchall()

            count = len(itens)
            if show_message:
                QMessageBox.information(self, "Relatório", f"{count} itens encontrados.")

            for item in itens:
                row = self.report_table.rowCount()
                self.report_table.insertRow(row)
                
                self.report_table.setItem(row, 0, QTableWidgetItem(item['data_venda']))
                self.report_table.setItem(row, 1, QTableWidgetItem(str(item['numero_venda_terminal'])))
                self.report_table.setItem(row, 2, QTableWidgetItem(item['codigo_barras']))
                self.report_table.setItem(row, 3, QTableWidgetItem(item['descricao']))
                self.report_table.setItem(row, 4, QTableWidgetItem(f"{item['quantidade']:.2f}"))
                self.report_table.setItem(row, 5, QTableWidgetItem(f"R$ {item['preco_unitario']:.2f}"))
                self.report_table.setItem(row, 6, QTableWidgetItem(f"R$ {item['total_item']:.2f}"))
                
            if count > 0:
                self.btn_export_pdf.setEnabled(True)
                self.btn_export_xlsx.setEnabled(True)
            else:
                self.btn_export_pdf.setEnabled(False)
                self.btn_export_xlsx.setEnabled(False)

        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao carregar relatório de produtos: {e}")
        finally:
            conn.close()

    def _get_table_data(self):
        """Lê os dados e cabeçalhos da QTableWidget para exportação."""
        headers = []
        for j in range(self.report_table.columnCount()):
            headers.append(self.report_table.horizontalHeaderItem(j).text())
        
        data = []
        for i in range(self.report_table.rowCount()):
            row_data = []
            for j in range(self.report_table.columnCount()):
                item = self.report_table.item(i, j)
                row_data.append(item.text() if item else "")
            data.append(row_data)
        return headers, data

    def _export_pdf(self):
        try:
            headers, data = self._get_table_data()
            title = "Relatório de Vendas por Produto"
            export_to_pdf(headers, data, title, self)
        except Exception as e:
            QMessageBox.critical(self, "Erro ao Exportar PDF", f"Falha ao gerar PDF: {e}")
            
    def _export_xlsx(self):
        try:
            headers, data = self._get_table_data()
            export_to_xlsx(headers, data, self)
        except Exception as e:
            QMessageBox.critical(self, "Erro ao Exportar XLSX", f"Falha ao gerar Excel: {e}")