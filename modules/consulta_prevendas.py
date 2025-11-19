# -*- coding: utf-8 -*-
# modules/consulta_prevendas.py
import sqlite3
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, 
    QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView, 
    QAbstractItemView, QDateEdit, QCalendarWidget, QComboBox,
    QFrame, QLineEdit, QGridLayout
)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, QDate
from database.db import get_connection
from .report_exporter import export_to_pdf, export_to_xlsx # Reutiliza nosso exportador

class ConsultaPreVendas(QWidget):
    """
    Tela para consultar Vendas Não-Fiscais (Pré-Vendas/Comandas)
    que estão pagas e aguardando atendimento/conversão.
    """
    def __init__(self, user_id, **kwargs):
        super().__init__()
        self.user_id = user_id
        self.setWindowTitle("Consulta de Vendas Não-Fiscais (Pré-Vendas)")
        
        self._setup_styles()
        self._build_ui()
        self._connect_signals()
        
        self.load_report(show_message=False) 

    def _setup_styles(self):
        # (Estilo reutilizado dos outros relatórios)
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
        
        # --- 1. PAINEL DE FILTROS ---
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
        
        # Filtro de Número da Venda (para o operador achar)
        filter_layout.addWidget(QLabel("Nº Venda:"), 2, 2)
        self.venda_num_input = QLineEdit()
        self.venda_num_input.setPlaceholderText("Ex: 123")
        filter_layout.addWidget(self.venda_num_input, 2, 3)

        self.btn_filtrar = QPushButton("Filtrar")
        filter_layout.addWidget(self.btn_filtrar, 2, 4)
        
        # Botões de Exportação
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

        # --- 2. TABELA DE RESULTADOS ---
        self.report_table = QTableWidget()
        self.report_table.setColumnCount(7)
        self.report_table.setHorizontalHeaderLabels([
            "ID Venda", "Nº Venda (Não-Fiscal)", "Data/Hora", "Cliente", "Terminal", 
            "Operador", "Valor Total"
        ])
        self.report_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.report_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.report_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.report_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.report_table.setColumnHidden(0, True) # Oculta o ID real da venda
        
        main_layout.addWidget(self.report_table)
        
        self._load_filters()

    def _load_filters(self):
        """Carrega os filtros dos ComboBoxes."""
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
        self.venda_num_input.returnPressed.connect(lambda: self.load_report(show_message=True))
        self.btn_export_pdf.clicked.connect(self._export_pdf)
        self.btn_export_xlsx.clicked.connect(self._export_xlsx)

    def load_report(self, show_message=False):
        """Carrega os dados do relatório com base nos filtros."""
        self.report_table.setRowCount(0)
        
        date_start_str = self.date_start.date().toString("yyyy-MM-dd") + " 00:00:00"
        date_end_str = self.date_end.date().toString("yyyy-MM-dd") + " 23:59:59"
        empresa_id = self.empresa_combo.currentData()
        terminal_id = self.terminal_combo.currentData()
        venda_num = self.venda_num_input.text().strip()
        
        conn = get_connection()
        try:
            cur = conn.cursor()
            
            # Query foca em Vendas Não-Fiscais que estão Finalizadas (Pagas)
            query = """
                SELECT 
                    v.id, v.numero_venda_terminal, v.data_venda, v.total_final,
                    c.nome_razao,
                    t.nome_terminal,
                    u.username
                FROM vendas v
                JOIN clientes c ON v.cliente_id = c.id
                JOIN terminais_pdv t ON v.terminal_id = t.id
                JOIN usuarios u ON v.user_id = u.id
                WHERE v.data_venda BETWEEN ? AND ?
                  AND v.tipo_documento = 'NAO_FISCAL' 
                  AND v.status = 'FINALIZADA'
            """
            params = [date_start_str, date_end_str]
            
            if empresa_id:
                query += " AND v.empresa_id = ?"
                params.append(empresa_id)
            if terminal_id:
                query += " AND v.terminal_id = ?"
                params.append(terminal_id)
            if venda_num:
                query += " AND v.numero_venda_terminal = ?"
                params.append(venda_num)
                
            query += " ORDER BY v.data_venda DESC"
            
            cur.execute(query, tuple(params))
            vendas = cur.fetchall()

            if show_message:
                QMessageBox.information(self, "Relatório", f"{len(vendas)} vendas não-fiscais pendentes encontradas.")

            for venda in vendas:
                row = self.report_table.rowCount()
                self.report_table.insertRow(row)
                
                self.report_table.setItem(row, 0, QTableWidgetItem(str(venda['id'])))
                self.report_table.setItem(row, 1, QTableWidgetItem(str(venda['numero_venda_terminal'])))
                self.report_table.setItem(row, 2, QTableWidgetItem(venda['data_venda']))
                self.report_table.setItem(row, 3, QTableWidgetItem(venda['nome_razao']))
                self.report_table.setItem(row, 4, QTableWidgetItem(venda['nome_terminal']))
                self.report_table.setItem(row, 5, QTableWidgetItem(venda['username']))
                self.report_table.setItem(row, 6, QTableWidgetItem(f"R$ {venda['total_final']:.2f}"))
                
            if self.report_table.rowCount() > 0:
                self.btn_export_pdf.setEnabled(True)
                self.btn_export_xlsx.setEnabled(True)
            else:
                self.btn_export_pdf.setEnabled(False)
                self.btn_export_xlsx.setEnabled(False)

        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao carregar consulta: {e}")
        finally:
            conn.close()

    def _get_table_data(self):
        """Lê os dados e cabeçalhos da QTableWidget para exportação."""
        headers = []
        for j in range(self.report_table.columnCount()):
            if not self.report_table.isColumnHidden(j):
                headers.append(self.report_table.horizontalHeaderItem(j).text())
        
        data = []
        for i in range(self.report_table.rowCount()):
            row_data = []
            for j in range(self.report_table.columnCount()):
                if not self.report_table.isColumnHidden(j):
                    item = self.report_table.item(i, j)
                    row_data.append(item.text() if item else "")
            data.append(row_data)
        return headers, data

    def _export_pdf(self):
        try:
            headers, data = self._get_table_data()
            title = "Relatório de Vendas Não-Fiscais (Pendentes)"
            export_to_pdf(headers, data, title, self)
        except Exception as e:
            QMessageBox.critical(self, "Erro ao Exportar PDF", f"Falha ao gerar PDF: {e}")
            
    def _export_xlsx(self):
        try:
            headers, data = self._get_table_data()
            export_to_xlsx(headers, data, self)
        except Exception as e:
            QMessageBox.critical(self, "Erro ao Exportar XLSX", f"Falha ao gerar Excel: {e}")