# -*- coding: utf-8 -*-
# modules/relatorio_dre_form.py
import sqlite3
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, 
    QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView, 
    QAbstractItemView, QDateEdit, QCalendarWidget, QComboBox,
    QFrame, QGridLayout, QFileDialog
)
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtCore import Qt, QDate
from database.db import get_connection
from .report_exporter import export_to_pdf, export_to_xlsx

class RelatorioDREForm(QWidget):
    """
    Relatório DRE (Demonstrativo de Resultado do Exercício)
    Baseado em Regime de Caixa (Lançamentos Pagos).
    """
    def __init__(self, user_id, **kwargs):
        super().__init__()
        self.user_id = user_id
        self.setWindowTitle("Relatório DRE (Regime de Caixa)")
        
        self.company_map = {}
        
        self._setup_styles()
        self._build_ui()
        self._connect_signals()
        
        self._load_filters()
        self.load_report(show_message=False) 

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
            QDateEdit, QComboBox {
                border: 1px solid #c0c0d0; border-radius: 5px; 
                padding: 6px; background-color: white;
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
        self.date_start.setDate(QDate.currentDate().addDays(-QDate.currentDate().day() + 1)) # Primeiro dia do mês
        self.date_start.setCalendarPopup(True)
        filter_layout.addWidget(self.date_start, 0, 1)
        
        filter_layout.addWidget(QLabel("Data Fim:"), 0, 2)
        self.date_end = QDateEdit(QDate.currentDate())
        self.date_end.setCalendarPopup(True)
        filter_layout.addWidget(self.date_end, 0, 3)
        
        filter_layout.addWidget(QLabel("Empresa:"), 1, 0)
        self.empresa_combo = QComboBox()
        filter_layout.addWidget(self.empresa_combo, 1, 1, 1, 3)
        
        self.btn_filtrar = QPushButton("Gerar Relatório")
        filter_layout.addWidget(self.btn_filtrar, 1, 4)
        
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

        filter_layout.addLayout(export_layout, 1, 5)
        filter_layout.setColumnStretch(6, 1)
        
        main_layout.addWidget(filter_frame)

        self.report_table = QTableWidget()
        self.report_table.setColumnCount(2)
        self.report_table.setHorizontalHeaderLabels(["Descrição (Plano de Contas)", "Valor (R$)"])
        self.report_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.report_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.report_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        main_layout.addWidget(self.report_table)

    def _load_filters(self):
        conn = get_connection()
        try:
            cur_emp = conn.cursor()
            cur_emp.execute("SELECT id, razao_social FROM empresas WHERE status = 1 ORDER BY razao_social")
            self.empresa_combo.addItem("Todas as Empresas", None)
            for emp in cur_emp.fetchall():
                self.empresa_combo.addItem(emp['razao_social'], emp['id'])
            # Seleciona a Empresa 1 por padrão
            index_emp_1 = self.empresa_combo.findData(1)
            if index_emp_1 > -1:
                self.empresa_combo.setCurrentIndex(index_emp_1)
                
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao carregar filtros: {e}")
        finally:
            conn.close()

    def _connect_signals(self):
        self.btn_filtrar.clicked.connect(lambda: self.load_report(show_message=True))
        self.btn_export_pdf.clicked.connect(self._export_pdf)
        self.btn_export_xlsx.clicked.connect(self._export_xlsx)

    def load_report(self, show_message=False):
        """Carrega os dados do DRE com base nos filtros."""
        self.report_table.setRowCount(0)
        
        date_start_str = self.date_start.date().toString("yyyy-MM-dd")
        date_end_str = self.date_end.date().toString("yyyy-MM-dd")
        empresa_id = self.empresa_combo.currentData()
        
        conn = get_connection()
        try:
            cur = conn.cursor()
            
            # Query principal que agrupa por categoria
            query = """
                SELECT 
                    c.nome as categoria_nome,
                    c.tipo as categoria_tipo,
                    SUM(l.valor_pago) as total_pago
                FROM lancamentos_financeiros l
                JOIN categorias_financeiras c ON l.categoria_id = c.id
                JOIN titulos_financeiros t ON l.titulo_id = t.id
                WHERE l.status = 'PAGO'
                  AND l.data_pagamento BETWEEN ? AND ?
            """
            params = [date_start_str, date_end_str]
            
            if empresa_id:
                query += " AND t.empresa_id = ?"
                params.append(empresa_id)
                
            query += " GROUP BY c.id, c.nome, c.tipo ORDER BY c.tipo DESC, total_pago DESC"
            
            cur.execute(query, tuple(params))
            
            lancamentos = cur.fetchall()
            
            total_receitas = 0.0
            total_despesas = 0.0
            receitas_list = []
            despesas_list = []
            
            for lanc in lancamentos:
                if lanc['categoria_tipo'] == 'RECEITA':
                    total_receitas += lanc['total_pago']
                    receitas_list.append((lanc['categoria_nome'], lanc['total_pago']))
                else: # DESPESA
                    total_despesas += lanc['total_pago']
                    despesas_list.append((lanc['categoria_nome'], lanc['total_pago']))
            
            resultado = total_receitas - total_despesas
            
            # --- Preenche a Tabela ---
            
            # 1. Receitas
            row = self._insert_header_row("RECEITAS")
            for nome, valor in receitas_list:
                self._insert_data_row(f"    {nome}", valor)
            self._insert_total_row("TOTAL DE RECEITAS", total_receitas, QColor("#27AE60"))
            
            # 2. Despesas
            self._insert_spacer_row()
            row = self._insert_header_row("DESPESAS")
            for nome, valor in despesas_list:
                self._insert_data_row(f"    {nome}", valor)
            self._insert_total_row("TOTAL DE DESPESAS", total_despesas, QColor("#c0392b"))

            # 3. Resultado
            self._insert_spacer_row()
            cor_resultado = QColor("#0078d7") if resultado >= 0 else QColor("#c0392b")
            self._insert_total_row("RESULTADO LÍQUIDO (LUCRO/PREJUÍZO)", resultado, cor_resultado, 14)
            
            
            count = self.report_table.rowCount()
            if show_message:
                QMessageBox.information(self, "Relatório", f"DRE gerado com sucesso. {len(lancamentos)} grupos de lançamentos encontrados.")
            
            if count > 0:
                self.btn_export_pdf.setEnabled(True)
                self.btn_export_xlsx.setEnabled(True)
            else:
                self.btn_export_pdf.setEnabled(False)
                self.btn_export_xlsx.setEnabled(False)
                
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao carregar relatório DRE: {e}")
        finally:
            conn.close()

    # --- Funções de ajuda para popular a tabela ---
    
    def _insert_header_row(self, text):
        row = self.report_table.rowCount()
        self.report_table.insertRow(row)
        item_desc = QTableWidgetItem(text)
        item_desc.setFont(QFont("Segoe UI", 12, QFont.Bold))
        item_desc.setBackground(QColor("#e0e0e0"))
        item_valor = QTableWidgetItem("")
        item_valor.setBackground(QColor("#e0e0e0"))
        self.report_table.setItem(row, 0, item_desc)
        self.report_table.setItem(row, 1, item_valor)
        return row
        
    def _insert_data_row(self, text, valor):
        row = self.report_table.rowCount()
        self.report_table.insertRow(row)
        item_desc = QTableWidgetItem(text)
        
        item_valor = QTableWidgetItem(f"R$ {valor:.2f}")
        item_valor.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        self.report_table.setItem(row, 0, item_desc)
        self.report_table.setItem(row, 1, item_valor)
        return row
        
    def _insert_total_row(self, text, valor, color, font_size=12):
        row = self.report_table.rowCount()
        self.report_table.insertRow(row)
        
        item_desc = QTableWidgetItem(text)
        item_desc.setFont(QFont("Segoe UI", font_size, QFont.Bold))
        item_desc.setForeground(color)
        
        item_valor = QTableWidgetItem(f"R$ {valor:.2f}")
        item_valor.setFont(QFont("Segoe UI", font_size, QFont.Bold))
        item_valor.setForeground(color)
        item_valor.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        self.report_table.setItem(row, 0, item_desc)
        self.report_table.setItem(row, 1, item_valor)
        return row
        
    def _insert_spacer_row(self):
        row = self.report_table.rowCount()
        self.report_table.insertRow(row)
        self.report_table.setRowHeight(row, 10) # Linha fina
        item1 = QTableWidgetItem("")
        item1.setBackground(QColor("#f8f8fb"))
        item2 = QTableWidgetItem("")
        item2.setBackground(QColor("#f8f8fb"))
        self.report_table.setItem(row, 0, item1)
        self.report_table.setItem(row, 1, item2)

    # --- Funções de Exportação ---

    def _get_table_data(self):
        """Lê os dados e cabeçalhos da QTableWidget para exportação."""
        headers = ["Descrição", "Valor (R$)"]
        
        data = []
        for i in range(self.report_table.rowCount()):
            row_data = []
            # Coluna 0 (Descrição)
            item_desc = self.report_table.item(i, 0)
            row_data.append(item_desc.text() if item_desc else "")
            # Coluna 1 (Valor)
            item_valor = self.report_table.item(i, 1)
            row_data.append(item_valor.text() if item_valor else "")
            
            data.append(row_data)
        return headers, data

    def _export_pdf(self):
        try:
            headers, data = self._get_table_data()
            title = f"Relatório DRE (Regime de Caixa) - {self.date_start.text()} a {self.date_end.text()}"
            export_to_pdf(headers, data, title, self, orientation='portrait')
        except Exception as e:
            QMessageBox.critical(self, "Erro ao Exportar PDF", f"Falha ao gerar PDF: {e}")
            
    def _export_xlsx(self):
        try:
            headers, data = self._get_table_data()
            export_to_xlsx(headers, data, self)
        except Exception as e:
            QMessageBox.critical(self, "Erro ao Exportar XLSX", f"Falha ao gerar Excel: {e}")