# modules/z_report_view.py
import sqlite3
from PyQt5.QtWidgets import (
    QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, 
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QGridLayout,
    QMessageBox, QTabWidget, QWidget, QTextEdit
)
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtCore import Qt, QPoint
from database.db import get_connection
from . import printing_service 

class ZReportView(QDialog):
    """
    Diálogo para visualização do Relatório Z (Leitura X) antes do fechamento.
    Exibe abas Sintético e Analítico.
    """
    def __init__(self, caixa_id, terminal_id, conferencia_data, parent=None):
        super().__init__(parent)
        self.caixa_id = caixa_id
        self.terminal_id = terminal_id
        self.conferencia_data = conferencia_data 
        self.old_pos = None
        self._centered = False

        self.setWindowTitle("Relatório de Fechamento de Caixa (Leitura X)")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(800, 600)
        self.setModal(True)
        
        self._setup_styles()
        self._build_ui()
        
        self._load_report_data()

    def _setup_styles(self):
        self.setStyleSheet("""
            QDialog { background-color: transparent; }
            QFrame#main_frame {
                background-color: #f8f8fb; border-radius: 8px; border: 1px solid #c0c0d0;
            }
            QFrame#title_bar {
                background-color: #e0e8f0; border-top-left-radius: 8px;
                border-top-right-radius: 8px; border-bottom: 1px solid #c0c0d0;
                height: 35px;
            }
            QLabel#title_label { font-size: 14px; font-weight: bold; color: #333; }
            QPushButton#btn_imprimir { background-color: #2ECC71; color: white; }
            QPushButton#btn_fechar { background-color: #0078d7; color: white; }
            
            QTabWidget::pane { border-top: 1px solid #c0c0d0; background: #fdfdfd; }
            QTabBar::tab { background: #e0e0e0; padding: 10px 25px; }
            QTabBar::tab:selected { background: #fdfdfd; border: 1px solid #c0c0d0; border-bottom: none; }
            
            QTextEdit {
                font-family: 'Courier New', Courier, monospace;
                background-color: #ffffff;
                border: 1px solid #c0c0d0;
                color: #333;
                font-size: 13px;
            }
            QTableWidget {
                border: 1px solid #c0c0d0;
                selection-background-color: #0078d7; font-size: 14px;
            }
            QHeaderView::section {
                background-color: #e8e8e8; padding: 8px;
                border: 1px solid #c0c0d0; font-weight: bold; font-size: 14px;
            }
        """)

    def _build_ui(self):
        main_frame = QFrame(self)
        main_frame.setObjectName("main_frame")
        layout = QVBoxLayout(main_frame)
        layout.setContentsMargins(1, 1, 1, 10)

        # 1. Barra de Título
        self.title_bar = QFrame()
        self.title_bar.setObjectName("title_bar")
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(10, 0, 10, 0)
        self.title_label = QLabel("Relatório de Fechamento", objectName="title_label")
        title_layout.addWidget(self.title_label)
        layout.addWidget(self.title_bar)

        # 2. Abas
        self.tabs = QTabWidget()
        self.tab_sintetico = QWidget()
        self.tab_analitico = QWidget()
        
        self.tabs.addTab(self.tab_sintetico, "Relatório Sintético")
        self.tabs.addTab(self.tab_analitico, "Relatório Analítico (Vendas)")
        
        layout.addWidget(self.tabs)
        
        # --- Layout Aba Sintético (Texto) ---
        layout_sintetico = QVBoxLayout(self.tab_sintetico)
        self.report_sintetico_text = QTextEdit()
        self.report_sintetico_text.setReadOnly(True)
        layout_sintetico.addWidget(self.report_sintetico_text)
        
        # --- Layout Aba Analítico (Tabela) ---
        layout_analitico = QVBoxLayout(self.tab_analitico)
        self.report_analitico_table = QTableWidget()
        self.report_analitico_table.setColumnCount(6) # +1 Coluna Status
        self.report_analitico_table.setHorizontalHeaderLabels(["Nº Venda", "Status", "Data/Hora", "Cliente", "Itens", "Valor Total"])
        self.report_analitico_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.report_analitico_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout_analitico.addWidget(self.report_analitico_table)

        # 3. Botões
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_imprimir = QPushButton("Imprimir Relatório (F10)")
        self.btn_imprimir.setObjectName("btn_imprimir")
        self.btn_imprimir.setShortcut("F10")
        self.btn_imprimir.clicked.connect(self._print_report)
        
        self.btn_fechar = QPushButton("Confirmar e Fechar (Esc)")
        self.btn_fechar.setObjectName("btn_fechar")
        self.btn_fechar.setShortcut("Esc")
        self.btn_fechar.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.btn_imprimir)
        btn_layout.addWidget(self.btn_fechar)
        layout.addLayout(btn_layout)
        
        dialog_layout = QVBoxLayout(self)
        dialog_layout.setContentsMargins(0,0,0,0)
        dialog_layout.addWidget(main_frame)

    def showEvent(self, event):
        super().showEvent(event)
        if self.parent() and not self._centered:
            parent_global_center = self.parent().mapToGlobal(self.parent().rect().center())
            dialog_center = self.rect().center()
            self.move(parent_global_center - dialog_center)
            self._centered = True
            
    def _load_report_data(self):
        """Busca os dados do DB para preencher os relatórios."""
        conn = get_connection()
        try:
            # --- Dados para o Relatório Analítico ---
            cur_analitico = conn.cursor()
            query_analitico = """
                SELECT 
                    v.numero_venda_terminal, 
                    v.status,
                    v.data_venda, 
                    c.nome_razao, 
                    COUNT(vi.id) as total_itens, 
                    v.total_final,
                    v.desconto_itens,
                    v.desconto_geral,
                    v.subtotal
                FROM vendas v
                JOIN clientes c ON v.cliente_id = c.id
                LEFT JOIN vendas_itens vi ON v.id = vi.venda_id
                WHERE v.caixa_id = ?
                GROUP BY v.id
                ORDER BY v.data_venda
            """
            cur_analitico.execute(query_analitico, (self.caixa_id,))
            vendas = cur_analitico.fetchall()
            
            self.report_analitico_table.setRowCount(0)
            for venda in vendas:
                row = self.report_analitico_table.rowCount()
                self.report_analitico_table.insertRow(row)
                
                # Cor para cancelados
                color = QColor("#e74c3c") if venda['status'] == 'CANCELADA' else QColor("#000000")
                
                item_num = QTableWidgetItem(str(venda['numero_venda_terminal']))
                item_num.setForeground(color)
                self.report_analitico_table.setItem(row, 0, item_num)
                
                item_status = QTableWidgetItem(venda['status'])
                item_status.setForeground(color)
                self.report_analitico_table.setItem(row, 1, item_status)
                
                self.report_analitico_table.setItem(row, 2, QTableWidgetItem(venda['data_venda']))
                self.report_analitico_table.setItem(row, 3, QTableWidgetItem(venda['nome_razao']))
                self.report_analitico_table.setItem(row, 4, QTableWidgetItem(str(venda['total_itens'])))
                
                item_total = QTableWidgetItem(f"R$ {venda['total_final']:.2f}")
                item_total.setForeground(color)
                self.report_analitico_table.setItem(row, 5, item_total)

            # --- Dados para o Relatório Sintético ---
            cur_sintetico = conn.cursor()
            
            # Totais Válidos (FINALIZADA)
            total_subtotal = sum(v['subtotal'] for v in vendas if v['status'] == 'FINALIZADA')
            total_descontos = sum((v['desconto_itens'] + v['desconto_geral']) for v in vendas if v['status'] == 'FINALIZADA')
            total_liquido = sum(v['total_final'] for v in vendas if v['status'] == 'FINALIZADA')
            
            # Total Cancelado (Informativo)
            total_cancelado = sum(v['total_final'] for v in vendas if v['status'] == 'CANCELADA')

            # 1. Sessão e Empresa
            cur_sintetico.execute("SELECT * FROM caixa_sessoes WHERE id = ?", (self.caixa_id,))
            sessao = cur_sintetico.fetchone()
            
            cur_sintetico.execute("""
                SELECT t.nome_terminal, e.razao_social
                FROM terminais_pdv t
                JOIN empresas e ON t.empresa_id = e.id
                WHERE t.id = ?
            """, (self.terminal_id,))
            info_header = cur_sintetico.fetchone()
            
            cur_sintetico.execute("SELECT username FROM usuarios WHERE id = ?", (sessao['user_id'],))
            info_operador = cur_sintetico.fetchone()

            # 4. Pagamentos (APENAS DE VENDAS VÁLIDAS)
            cur_sintetico.execute("""
                SELECT vp.forma, SUM(vp.valor) as total_forma
                FROM vendas_pagamentos vp
                JOIN vendas v ON vp.venda_id = v.id
                WHERE v.caixa_id = ? AND v.status = 'FINALIZADA'
                GROUP BY vp.forma
            """, (self.caixa_id,))
            pagamentos = cur_sintetico.fetchall()

            # Monta o texto
            report_lines = []
            def add_line(texto, align='left', bold=False):
                if bold: texto = f"<b>{texto}</b>"
                if align == 'center':
                    report_lines.append(f"<p style='text-align: center;'>{texto}</p>")
                else:
                    report_lines.append(texto)
            def add_divider():
                report_lines.append("-" * 48)

            add_line(f"{info_header['razao_social'] if info_header else 'EMPRESA'}", 'center', bold=True)
            add_line(f"EXTRATO DE FECHAMENTO DE CAIXA", 'center', bold=True)
            add_divider()
            add_line(f"Terminal: {info_header['nome_terminal'] if info_header else 'N/A'}")
            add_line(f"Operador: {info_operador['username'] if info_operador else 'N/A'}")
            add_line(f"Abertura: {sessao['data_abertura']}")
            add_divider()
            
            add_line(f"<b>{'VALORES TOTAIS (VENDAS)':<30}{'R$':>18}</b>")
            add_line(f"{'Total Bruto':<30}{total_subtotal:>18.2f}")
            add_line(f"{'Total Descontos':<30}{-total_descontos:>18.2f}")
            add_line(f"{'TOTAL LÍQUIDO':<30}{total_liquido:>18.2f}")
            
            if total_cancelado > 0:
                add_line(f"<b>{'TOTAL CANCELADO (Info)':<30}{total_cancelado:>18.2f}</b>")
                
            add_divider()
            
            add_line(f"<b>{'MEIOS DE PAGAMENTO':<30}{'R$':>18}</b>")
            for pg in pagamentos:
                add_line(f"{pg['forma']:<30}{pg['total_forma']:>18.2f}")
            add_divider()

            add_line(f"<b>{'CONFERÊNCIA DE CAIXA':<30}{'R$':>18}</b>")
            add_line(f"{'1. Suprimento (Abertura)':<30}{sessao['valor_inicial']:>18.2f}")
            total_dinheiro_vendas = next((p['total_forma'] for p in pagamentos if p['forma'] == 'Dinheiro'), 0.0)
            add_line(f"{'2. Vendas em Dinheiro':<30}{total_dinheiro_vendas:>18.2f}")
            
            data_conf = self.conferencia_data
            add_line(f"{'TOTAL ESPERADO (1+2)':<30}{data_conf['calculado']:>18.2f}")
            add_line(f"{'TOTAL INFORMADO':<30}{data_conf['informado']:>18.2f}")
            add_divider()
            
            if abs(data_conf['diferenca']) < 0.01:
                add_line(f"<b>{'DIFERENÇA:':<30}{'R$ 0.00':>18}</b>")
            elif data_conf['diferenca'] > 0:
                add_line(f"<b>{'FALTA (Quebra):':<30}{-data_conf['diferenca']:>18.2f}</b>")
            else:
                add_line(f"<b>{'SOBRA:':<30}{abs(data_conf['diferenca']):>18.2f}</b>")

            self.report_sintetico_text.setHtml("<pre>" + "\n".join(report_lines) + "</pre>")

        except Exception as e:
            QMessageBox.critical(self, "Erro ao Gerar Relatório", f"Erro: {e}")
        finally:
            if conn: conn.close()

    def _print_report(self):
        report_text = self.report_sintetico_text.toPlainText()
        try:
            printing_service.generate_and_print_z_report(
                report_text=report_text,
                terminal_id=self.terminal_id 
            )
        except Exception as e:
            QMessageBox.critical(self, "Erro de Impressão", f"Falha ao imprimir: {e}")

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