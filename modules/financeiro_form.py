# -*- coding: utf-8 -*-
# modules/financeiro_form.py
import sqlite3
import datetime
import logging # <-- NOVO
from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, 
    QMessageBox, QGridLayout, QFrame, QTableWidget, QHeaderView, 
    QTableWidgetItem, QAbstractItemView, QStackedWidget, QComboBox,
    QTabWidget, QDateEdit,QDialog
)
from PyQt5.QtCore import Qt, QDate, QLocale
from PyQt5.QtGui import QFont, QColor
from database.db import get_connection
from .lancamento_dialog import LancamentoDialog # Importa o diálogo de lançamento
from .baixa_lancamento_dialog import BaixaLancamentoDialog # Importa o diálogo de baixa
from .edit_lancamento_dialog import EditLancamentoDialog # Importa o diálogo de edição

# --- NOVAS IMPORTAÇÕES PARA GRÁFICOS ---
try:
    import pyqtgraph as pg
    from pyqtgraph import BarGraphItem
except ImportError:
    print("PyQtGraph não instalado. Gráficos não funcionarão.")
    pg = None # Define como None para evitar quebra
# --- FIM DAS NOVAS IMPORTAÇÕES ---


class FinanceiroForm(QWidget):
    """
    Módulo Central Financeiro: Dashboard, Contas a Pagar/Receber e Lançamentos.
    Req. #4, #5, #8 do Módulo Financeiro.
    """
    def __init__(self, user_id, **kwargs):
        super().__init__()
        self.user_id = user_id
        self.empresa_id = 1 # Assume a empresa 1 por padrão
        self.setWindowTitle("Gestão Financeira")
        
        # --- NOVO: Logger ---
        self.logger = logging.getLogger(__name__)
        
        self.contas_map = {} # {id: nome}
        self.categorias_map = {} # {id: (nome, tipo)}
        self.centros_custo_map = {} # {id: nome}
        self.parceiros_map = {} # {tipo_id: nome}
        
        # --- Referências dos Gráficos ---
        self.graph_fluxo_caixa = None
        self.graph_desp_categoria = None
        
        self._setup_styles()
        self._build_ui()
        self._connect_signals()
        
        self._load_all_maps()
        self.load_dashboard_data()
        self.load_lancamentos()

    def _setup_styles(self):
        # (Inalterado)
        self.setStyleSheet("""
            QWidget { background-color: #f8f8fb; font-family: 'Segoe UI'; }
            QLabel { font-weight: bold; color: #444; font-size: 13px; }
            
            QTabWidget::pane { border-top: 1px solid #c0c0d0; background: #fdfdfd; }
            QTabBar::tab { background: #e0e0e0; padding: 10px 25px; font-size: 14px; }
            QTabBar::tab:selected { background: #fdfdfd; border: 1px solid #c0c0d0; border-bottom: none; }

            QTableWidget {
                border: 1px solid #c0c0d0;
                selection-background-color: #0078d7; font-size: 14px;
            }
            QHeaderView::section {
                background-color: #e8e8e8; padding: 8px;
                border: 1px solid #c0c0d0; font-weight: bold; font-size: 14px;
            }
            
            QFrame#filter_frame, QFrame#kpi_frame, QFrame#graph_frame {
                background-color: #fdfdfd;
                border: 1px solid #c0c0d0;
                border-radius: 8px;
            }
            
            QDateEdit, QComboBox, QLineEdit {
                border: 1px solid #c0c0d0; border-radius: 5px; 
                padding: 6px; background-color: white;
            }
            
            QPushButton {
                background-color: #0078d7; color: white; border-radius: 6px;
                padding: 8px 15px; font-weight: bold;
            }
            QPushButton:hover { background-color: #005fa3; }
            QPushButton#btn_novo_lancamento { background-color: #2ECC71; }
            QPushButton#btn_novo_lancamento:hover { background-color: #27AE60; }
            QPushButton#btn_baixar { background-color: #f39c12; }
            QPushButton#btn_baixar:hover { background-color: #e67e22; }
            QPushButton#btn_estornar { background-color: #95A5A6; }
            QPushButton#btn_estornar:hover { background-color: #7F8C8D; }
            QPushButton#btn_excluir_lanc { background-color: #e74c3c; }
            QPushButton#btn_excluir_lanc:hover { background-color: #c0392b; }
            
            QPushButton#btn_conciliar { background-color: #27AE60; }
            QPushButton#btn_conciliar:hover { background-color: #229954; }
            QPushButton#btn_desconciliar { background-color: #7f8c8d; }
            QPushButton#btn_desconciliar:hover { background-color: #627071; }

            
            /* --- Estilos do Dashboard --- */
            QLabel.kpi_title { font-size: 13px; font-weight: bold; color: #7f8c8d; }
            QLabel.kpi_value_ok { font-size: 24px; font-weight: bold; color: #27AE60; }
            QLabel.kpi_value_bad { font-size: 24px; font-weight: bold; color: #e74c3c; }
            QLabel.kpi_value_neutral { font-size: 24px; font-weight: bold; color: #2980b9; }
            QLabel.graph_title { font-size: 15px; font-weight: bold; color: #333; }
            
            QFrame#graph_placeholder { border: none; }
        """)

    def _build_ui(self):
        # (Inalterado)
        main_layout = QVBoxLayout(self)
        
        # --- Toolbar Principal ---
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(0, 0, 0, 10)
        self.btn_novo_lancamento = QPushButton("Novo Lançamento (Despesa/Receita)")
        self.btn_novo_lancamento.setObjectName("btn_novo_lancamento")
        toolbar_layout.addWidget(self.btn_novo_lancamento)
        toolbar_layout.addStretch()
        main_layout.addLayout(toolbar_layout)

        # --- Abas Principais ---
        self.tabs = QTabWidget()
        self.tab_dashboard = QWidget()
        self.tab_lancamentos = QWidget()
        self.tab_extrato = QWidget()
        
        self.tabs.addTab(self.tab_dashboard, "Dashboard Financeiro")
        self.tabs.addTab(self.tab_lancamentos, "Lançamentos (A Pagar/Receber)")
        self.tabs.addTab(self.tab_extrato, "Extrato de Contas")
        
        main_layout.addWidget(self.tabs)
        
        self._build_tab_dashboard()
        self._build_tab_lancamentos()
        self._build_tab_extrato()

    def _build_tab_dashboard(self):
        # (Inalterado)
        layout = QVBoxLayout(self.tab_dashboard)
        
        # 1. KPIs (Indicadores)
        kpi_frame = QFrame()
        kpi_frame.setObjectName("kpi_frame")
        kpi_frame.setFixedHeight(90)
        kpi_layout = QHBoxLayout(kpi_frame)
        kpi_layout.setSpacing(15)
        
        kpi_saldo_layout = QVBoxLayout()
        kpi_saldo_layout.addWidget(QLabel("SALDO TOTAL (CONTAS)", objectName="kpi_title"))
        self.lbl_kpi_saldo = QLabel("R$ 0,00", objectName="kpi_value_neutral")
        kpi_saldo_layout.addWidget(self.lbl_kpi_saldo)
        kpi_layout.addLayout(kpi_saldo_layout)
        
        kpi_vencido_layout = QVBoxLayout()
        kpi_vencido_layout.addWidget(QLabel("A PAGAR (VENCIDO)", objectName="kpi_title"))
        self.lbl_kpi_vencido = QLabel("R$ 0,00", objectName="kpi_value_bad")
        kpi_vencido_layout.addWidget(self.lbl_kpi_vencido)
        kpi_layout.addLayout(kpi_vencido_layout)
        
        kpi_hoje_layout = QVBoxLayout()
        kpi_hoje_layout.addWidget(QLabel("A VENCER (HOJE)", objectName="kpi_title"))
        self.lbl_kpi_hoje = QLabel("R$ 0,00", objectName="kpi_value_neutral")
        kpi_hoje_layout.addWidget(self.lbl_kpi_hoje)
        kpi_layout.addLayout(kpi_hoje_layout)
        
        kpi_receber_layout = QVBoxLayout()
        kpi_receber_layout.addWidget(QLabel("A RECEBER (MÊS)", objectName="kpi_title"))
        self.lbl_kpi_receber = QLabel("R$ 0,00", objectName="kpi_value_ok")
        kpi_receber_layout.addWidget(self.lbl_kpi_receber)
        kpi_layout.addLayout(kpi_receber_layout)
        
        kpi_layout.addStretch()
        layout.addWidget(kpi_frame)
        
        # 2. Gráficos
        graph_panel_layout = QHBoxLayout()
        graph_panel_layout.setSpacing(10)
        
        graph_frame_1 = QFrame()
        graph_frame_1.setObjectName("graph_frame")
        graph_layout_1 = QVBoxLayout(graph_frame_1)
        graph_layout_1.addWidget(QLabel("Fluxo de Caixa (Próximos 30 dias)", objectName="graph_title"))
        
        if pg: 
            self.graph_fluxo_caixa = pg.PlotWidget()
            self._setup_graph_styles(self.graph_fluxo_caixa, "Data", "Valor (R$)")
            graph_layout_1.addWidget(self.graph_fluxo_caixa)
        else:
            graph_layout_1.addWidget(QLabel("Biblioteca PyQtGraph não instalada."))
            
        graph_frame_2 = QFrame()
        graph_frame_2.setObjectName("graph_frame")
        graph_layout_2 = QVBoxLayout(graph_frame_2)
        graph_layout_2.addWidget(QLabel("Despesas por Categoria (Mês Atual)", objectName="graph_title"))
        
        if pg:
            self.graph_desp_categoria = pg.PlotWidget()
            self._setup_graph_styles(self.graph_desp_categoria, "Valor (R$)", "Categoria", horizontal=True)
            graph_layout_2.addWidget(self.graph_desp_categoria)
        else:
            graph_layout_2.addWidget(QLabel("Biblioteca PyQtGraph não instalada."))
        
        graph_panel_layout.addWidget(graph_frame_1)
        graph_panel_layout.addWidget(graph_frame_2)
        layout.addLayout(graph_panel_layout)

    def _build_tab_lancamentos(self):
        # (Inalterado)
        layout = QVBoxLayout(self.tab_lancamentos)
        
        # --- Filtros ---
        filter_frame = QFrame()
        filter_frame.setObjectName("filter_frame")
        filter_layout = QGridLayout(filter_frame)
        
        filter_layout.addWidget(QLabel("Data Início:"), 0, 0)
        self.lanc_date_start = QDateEdit(QDate.currentDate().addMonths(-1))
        self.lanc_date_start.setCalendarPopup(True)
        filter_layout.addWidget(self.lanc_date_start, 0, 1)
        
        filter_layout.addWidget(QLabel("Data Fim:"), 0, 2)
        self.lanc_date_end = QDateEdit(QDate.currentDate().addMonths(1))
        self.lanc_date_end.setCalendarPopup(True)
        filter_layout.addWidget(self.lanc_date_end, 0, 3)
        
        filter_layout.addWidget(QLabel("Status:"), 1, 0)
        self.lanc_status_combo = QComboBox()
        self.lanc_status_combo.addItems(["PENDENTE", "TODOS", "PAGO", "VENCIDO"])
        filter_layout.addWidget(self.lanc_status_combo, 1, 1)
        
        filter_layout.addWidget(QLabel("Tipo:"), 1, 2)
        self.lanc_tipo_combo = QComboBox()
        self.lanc_tipo_combo.addItems(["TODOS", "A PAGAR", "A RECEBER"])
        filter_layout.addWidget(self.lanc_tipo_combo, 1, 3)
        
        self.btn_filtrar_lanc = QPushButton("Filtrar")
        filter_layout.addWidget(self.btn_filtrar_lanc, 1, 4)
        filter_layout.setColumnStretch(5, 1)
        
        layout.addWidget(filter_frame)

        # --- Tabela ---
        self.lanc_table = QTableWidget()
        self.lanc_table.setColumnCount(9)
        self.lanc_table.setHorizontalHeaderLabels([
            "ID", "Vencimento", "Tipo", "Status", "Descrição", 
            "Categoria", "Centro Custo", "Valor Previsto", "Valor Pago"
        ])
        self.lanc_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.lanc_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.lanc_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.lanc_table.setColumnHidden(0, True)
        layout.addWidget(self.lanc_table)
        
        # --- Botões de Ação da Tabela ---
        table_btn_layout = QHBoxLayout()
        self.btn_baixar = QPushButton("Baixar Lançamento")
        self.btn_baixar.setObjectName("btn_baixar")
        self.btn_estornar = QPushButton("Estornar Baixa")
        self.btn_estornar.setObjectName("btn_estornar")
        self.btn_editar_lanc = QPushButton("Editar")
        self.btn_excluir_lanc = QPushButton("Excluir")
        self.btn_excluir_lanc.setObjectName("deleteButton")
        table_btn_layout.addStretch()
        table_btn_layout.addWidget(self.btn_baixar)
        table_btn_layout.addWidget(self.btn_estornar)
        table_btn_layout.addWidget(self.btn_editar_lanc)
        table_btn_layout.addWidget(self.btn_excluir_lanc)
        layout.addLayout(table_btn_layout)

    def _build_tab_extrato(self):
        # (Inalterado)
        layout = QVBoxLayout(self.tab_extrato)
        
        # --- Filtros ---
        filter_frame = QFrame()
        filter_frame.setObjectName("filter_frame")
        filter_layout = QGridLayout(filter_frame)
        
        filter_layout.addWidget(QLabel("Conta Financeira:"), 0, 0)
        self.extrato_conta_combo = QComboBox()
        filter_layout.addWidget(self.extrato_conta_combo, 0, 1)
        
        self.btn_filtrar_extrato = QPushButton("Gerar Extrato")
        filter_layout.addWidget(self.btn_filtrar_extrato, 0, 2)
        filter_layout.setColumnStretch(3, 1)
        
        layout.addWidget(filter_frame)

        # --- Tabela (Nova coluna) ---
        self.extrato_table = QTableWidget()
        self.extrato_table.setColumnCount(6) # <-- MUDOU DE 5 PARA 6
        self.extrato_table.setHorizontalHeaderLabels([
            "ID Mov.", "Data", "Tipo", "Descrição", "Valor (R$)", "Conciliado?"
        ])
        self.extrato_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.extrato_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.extrato_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.extrato_table.setColumnHidden(0, True)
        layout.addWidget(self.extrato_table)
        
        # --- Novos Botões de Conciliação ---
        conciliacao_layout = QHBoxLayout()
        conciliacao_layout.addStretch()
        self.btn_conciliar = QPushButton("✔️ Conciliar Lançamento")
        self.btn_conciliar.setObjectName("btn_conciliar")
        self.btn_desconciliar = QPushButton("✖️ Desconciliar Lançamento")
        self.btn_desconciliar.setObjectName("btn_desconciliar")
        conciliacao_layout.addWidget(self.btn_conciliar)
        conciliacao_layout.addWidget(self.btn_desconciliar)
        layout.addLayout(conciliacao_layout)

    def _connect_signals(self):
        # (Inalterado)
        self.btn_novo_lancamento.clicked.connect(self._open_new_lancamento_dialog)
        self.btn_filtrar_lanc.clicked.connect(self.load_lancamentos)
        self.btn_filtrar_extrato.clicked.connect(self.load_extrato)
        
        self.btn_baixar.clicked.connect(self._prompt_baixar_lancamento)
        self.btn_excluir_lanc.clicked.connect(self._delete_lancamento)
        self.btn_estornar.clicked.connect(self._prompt_estornar_lancamento)
        self.btn_editar_lanc.clicked.connect(self._prompt_edit_lancamento)
        
        self.btn_conciliar.clicked.connect(lambda: self._conciliar_movimento(conciliar=True))
        self.btn_desconciliar.clicked.connect(lambda: self._conciliar_movimento(conciliar=False))

    def _load_all_maps(self):
        # (Inalterado)
        conn = get_connection()
        try:
            cur = conn.cursor()
            
            # Contas (para Extrato)
            cur.execute("SELECT id, nome FROM contas_financeiras WHERE empresa_id = ? AND active = 1 ORDER BY nome", (self.empresa_id,))
            self.extrato_conta_combo.clear()
            self.contas_map.clear()
            self.extrato_conta_combo.addItem("Selecione uma conta...", None)
            for c in cur.fetchall():
                self.contas_map[c['id']] = c['nome']
                self.extrato_conta_combo.addItem(c['nome'], c['id'])
                
            # Categorias
            cur.execute("SELECT id, nome, tipo FROM categorias_financeiras ORDER BY nome")
            self.categorias_map.clear()
            for c in cur.fetchall():
                self.categorias_map[c['id']] = (c['nome'], c['tipo'])
                
            # Centros de Custo
            cur.execute("SELECT id, nome FROM centros_de_custo WHERE empresa_id = ? ORDER BY nome", (self.empresa_id,))
            self.centros_custo_map.clear()
            for c in cur.fetchall():
                self.centros_custo_map[c['id']] = c['nome']

            # Parceiros (Clientes/Fornecedores)
            self.parceiros_map.clear()
            cur.execute("SELECT id, nome_razao FROM clientes")
            for p in cur.fetchall():
                self.parceiros_map[f"C_{p['id']}"] = p['nome_razao']
            cur.execute("SELECT id, nome FROM fornecedores")
            for p in cur.fetchall():
                self.parceiros_map[f"F_{p['id']}"] = p['nome']
                
        except Exception as e:
            QMessageBox.critical(self, "Erro ao Carregar Dados", f"Erro: {e}")
        finally:
            conn.close()

    def load_dashboard_data(self):
        # (Inalterado)
        conn = get_connection()
        try:
            cur = conn.cursor()
            
            # 1. Saldo Total
            cur.execute("SELECT SUM(saldo_atual) as saldo_total FROM contas_financeiras WHERE empresa_id = ? AND active = 1", (self.empresa_id,))
            saldo = cur.fetchone()['saldo_total'] or 0.0
            self.lbl_kpi_saldo.setText(f"R$ {saldo:.2f}")
            self.lbl_kpi_saldo.setObjectName("kpi_value_ok" if saldo >= 0 else "kpi_value_bad")
            
            # 2. Contas a Pagar (Vencido)
            cur.execute("""
                SELECT SUM(valor_previsto - IFNULL(valor_pago, 0)) as total_vencido 
                FROM lancamentos_financeiros
                WHERE tipo = 'A PAGAR' AND status != 'PAGO' AND data_vencimento < DATE('now')
            """)
            vencido = cur.fetchone()['total_vencido'] or 0.0
            self.lbl_kpi_vencido.setText(f"R$ {vencido:.2f}")

            # 3. Contas a Vencer (Hoje)
            cur.execute("""
                SELECT SUM(valor_previsto - IFNULL(valor_pago, 0)) as total_hoje
                FROM lancamentos_financeiros
                WHERE status != 'PAGO' AND data_vencimento = DATE('now')
            """)
            hoje = cur.fetchone()['total_hoje'] or 0.0
            self.lbl_kpi_hoje.setText(f"R$ {hoje:.2f}")

            # 4. A Receber (Mês)
            cur.execute("""
                SELECT SUM(valor_previsto - IFNULL(valor_pago, 0)) as total_receber
                FROM lancamentos_financeiros
                WHERE tipo = 'A RECEBER' AND status != 'PAGO' 
                  AND STRFTIME('%Y-%m', data_vencimento) = STRFTIME('%Y-%m', 'now')
            """)
            receber = cur.fetchone()['total_receber'] or 0.0
            self.lbl_kpi_receber.setText(f"R$ {receber:.2f}")
            
            if pg: 
                self._load_graph_fluxo_caixa(conn)
                self._load_graph_desp_categoria(conn)
            
        except Exception as e:
            QMessageBox.critical(self, "Erro no Dashboard", f"Erro ao carregar KPIs: {e}")
        finally:
            conn.close()

    def load_lancamentos(self):
        # (Inalterado)
        self.lanc_table.setRowCount(0)
        
        conn = get_connection()
        try:
            cur = conn.cursor()
            
            query = """
                SELECT 
                    l.id, l.data_vencimento, l.tipo, l.status, l.descricao, 
                    l.categoria_id, l.centro_custo_id, 
                    l.valor_previsto, 
                    IFNULL(l.valor_pago, 0) as valor_pago
                FROM lancamentos_financeiros l
                JOIN titulos_financeiros t ON l.titulo_id = t.id
                WHERE t.empresa_id = ? 
            """
            params = [self.empresa_id]
            
            start_date = self.lanc_date_start.date().toString("yyyy-MM-dd")
            end_date = self.lanc_date_end.date().toString("yyyy-MM-dd")
            query += " AND l.data_vencimento BETWEEN ? AND ?"
            params.extend([start_date, end_date])
            
            status = self.lanc_status_combo.currentText()
            hoje = QDate.currentDate().toString("yyyy-MM-dd")
            
            if status == "PENDENTE":
                query += " AND l.status != 'PAGO'" # Mostra PENDENTE e VENCIDO
            elif status == "VENCIDO":
                 query += " AND l.status != 'PAGO' AND l.data_vencimento < ?"
                 params.append(hoje)
            elif status != "TODOS":
                query += " AND l.status = ?"
                params.append(status)
                
            tipo = self.lanc_tipo_combo.currentText()
            if tipo != "TODOS":
                query += " AND l.tipo = ?"
                params.append(tipo)
                
            query += " ORDER BY l.data_vencimento"
            
            cur.execute(query, tuple(params))
            
            for row in cur.fetchall():
                idx = self.lanc_table.rowCount()
                self.lanc_table.insertRow(idx)
                
                cat_nome = self.categorias_map.get(row['categoria_id'], ("-", "-"))[0]
                cc_nome = self.centros_custo_map.get(row['centro_custo_id'], "-")
                
                status_atual = row['status']
                if status_atual != 'PAGO' and row['data_vencimento'] < hoje:
                    status_atual = 'VENCIDO'
                
                self.lanc_table.setItem(idx, 0, QTableWidgetItem(str(row['id'])))
                self.lanc_table.setItem(idx, 1, QTableWidgetItem(row['data_vencimento']))
                self.lanc_table.setItem(idx, 2, QTableWidgetItem(row['tipo']))
                self.lanc_table.setItem(idx, 3, QTableWidgetItem(status_atual))
                self.lanc_table.setItem(idx, 4, QTableWidgetItem(row['descricao']))
                self.lanc_table.setItem(idx, 5, QTableWidgetItem(cat_nome))
                self.lanc_table.setItem(idx, 6, QTableWidgetItem(cc_nome))
                
                valor_previsto_item = QTableWidgetItem(f"{row['valor_previsto']:.2f}")
                valor_previsto_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.lanc_table.setItem(idx, 7, valor_previsto_item)
                
                valor_pago_item = QTableWidgetItem(f"{row['valor_pago']:.2f}")
                valor_pago_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.lanc_table.setItem(idx, 8, valor_pago_item)
                
                if status_atual == 'PAGO':
                    color = QColor("#dff0d8") # Verde claro
                elif status_atual == 'VENCIDO':
                    color = QColor("#f2dede") # Vermelho claro
                else:
                    color = QColor("white")
                    
                for j in range(self.lanc_table.columnCount()):
                    self.lanc_table.item(idx, j).setBackground(color)

        except Exception as e:
            QMessageBox.critical(self, "Erro ao Carregar Lançamentos", f"Erro: {e}")
        finally:
            conn.close()

    def load_extrato(self):
        # (Atualizado para incluir 'conciliado')
        self.extrato_table.setRowCount(0)
        conta_id = self.extrato_conta_combo.currentData()
        
        if conta_id is None:
            QMessageBox.warning(self, "Seleção", "Selecione uma conta financeira para gerar o extrato.")
            return

        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, data_movimento, tipo_movimento, descricao, valor, conciliado 
                FROM movimentacoes_contas
                WHERE conta_id = ?
                ORDER BY data_movimento DESC, id DESC
            """, (conta_id,))
            
            for mov in cur.fetchall():
                row = self.extrato_table.rowCount()
                self.extrato_table.insertRow(row)
                
                valor = mov['valor']
                if mov['tipo_movimento'] == 'SAIDA':
                    valor = -valor
                    color = QColor("#c0392b") # Vermelho
                else:
                    color = QColor("#27AE60") # Verde
                
                item_valor = QTableWidgetItem(f"R$ {valor:.2f}")
                item_valor.setForeground(color)
                item_valor.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

                is_conciliado = bool(mov['conciliado'])
                item_conc = QTableWidgetItem("✔️ Sim" if is_conciliado else "Não")
                item_conc.setTextAlignment(Qt.AlignCenter)
                item_conc.setForeground(QColor("#27AE60") if is_conciliado else QColor("#7f8c8d"))

                self.extrato_table.setItem(row, 0, QTableWidgetItem(str(mov['id'])))
                self.extrato_table.setItem(row, 1, QTableWidgetItem(mov['data_movimento']))
                self.extrato_table.setItem(row, 2, QTableWidgetItem(mov['tipo_movimento']))
                self.extrato_table.setItem(row, 3, QTableWidgetItem(mov['descricao']))
                self.extrato_table.setItem(row, 4, item_valor)
                self.extrato_table.setItem(row, 5, item_conc) # <-- NOVO

        except Exception as e:
            QMessageBox.critical(self, "Erro ao Carregar Extrato", f"Erro: {e}")
        finally:
            conn.close()
            
    def _open_new_lancamento_dialog(self):
        """Abre o diálogo de novo lançamento."""
        dialog = LancamentoDialog(self.user_id, self.empresa_id, self)
        
        if dialog.exec_() == QDialog.Accepted:
            self.logger.info(f"Usuário ID {self.user_id} criou um novo Título/Lançamento.")
            self.load_dashboard_data()
            self.load_lancamentos()
        else:
            self.tabs.setCurrentIndex(1) # Foca na aba de Lançamentos
            
    def _get_selected_lancamento(self):
        """Pega o ID e os dados completos do lançamento selecionado na tabela."""
        row = self.lanc_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Seleção", "Selecione um lançamento na tabela primeiro.")
            return None, None
        
        lancamento_id_str = self.lanc_table.item(row, 0).text()
        lancamento_id = int(lancamento_id_str)
        
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM lancamentos_financeiros WHERE id = ?", (lancamento_id,))
            data = cur.fetchone()
            if not data:
                QMessageBox.critical(self, "Erro", "Lançamento não encontrado no banco de dados.")
                return None, None
            return lancamento_id, dict(data)
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao buscar dados do lançamento: {e}")
            return None, None
        finally:
            conn.close()

    def _prompt_baixar_lancamento(self):
        """Abre o diálogo de baixa para o lançamento selecionado."""
        lancamento_id, data = self._get_selected_lancamento()
        if not lancamento_id:
            return
            
        if data['status'] == 'PAGO':
            QMessageBox.information(self, "Ação Inválida", "Este lançamento já está baixado (Pago).")
            return

        dialog = BaixaLancamentoDialog(self.user_id, self.empresa_id, data, self)
        
        if dialog.exec_() != QDialog.Accepted:
            return
            
        baixa_data = dialog.get_data()
        if not baixa_data:
            return # Validação falhou dentro do diálogo
            
        self._execute_baixa(lancamento_id, data, baixa_data)

    def _execute_baixa(self, lancamento_id, lancamento_data, baixa_data):
        """
        Executa a transação de baixa no banco de dados.
        (Atualiza lançamento, cria movimentação, atualiza saldo da conta)
        """
        
        tipo_movimento = "SAIDA" if lancamento_data['tipo'] == 'A PAGAR' else 'ENTRADA'
        valor_final_pago = baixa_data['valor_pago'] + baixa_data['juros'] - baixa_data['desconto']
        
        conn = get_connection()
        try:
            cur = conn.cursor()
            conn.execute("BEGIN")
            
            # 1. Cria a Movimentação na Conta Financeira
            desc_mov = f"Baixa Lançamento #{lancamento_id}: {lancamento_data['descricao']}"
            cur.execute("""
                INSERT INTO movimentacoes_contas
                (conta_id, lancamento_id, tipo_movimento, valor, data_movimento, descricao, conciliado)
                VALUES (?, ?, ?, ?, ?, ?, 0)
            """, (
                baixa_data['conta_id'], lancamento_id, tipo_movimento,
                valor_final_pago, baixa_data['data_pagamento'], desc_mov
            ))
            
            # 2. Atualiza o Saldo da Conta Financeira
            if tipo_movimento == 'SAIDA':
                cur.execute("UPDATE contas_financeiras SET saldo_atual = saldo_atual - ? WHERE id = ?", 
                            (valor_final_pago, baixa_data['conta_id']))
            else: # ENTRADA
                cur.execute("UPDATE contas_financeiras SET saldo_atual = saldo_atual + ? WHERE id = ?", 
                            (valor_final_pago, baixa_data['conta_id']))

            # 3. Atualiza o Lançamento Financeiro
            novo_valor_pago = (lancamento_data['valor_pago'] or 0.0) + valor_final_pago
            novo_status = 'PAGO' if not baixa_data['is_baixa_parcial'] else 'PENDENTE'
            
            cur.execute("""
                UPDATE lancamentos_financeiros
                SET 
                    status = ?,
                    data_pagamento = ?,
                    valor_pago = ?,
                    juros = IFNULL(juros, 0) + ?,
                    desconto = IFNULL(desconto, 0) + ?
                WHERE id = ?
            """, (
                novo_status, baixa_data['data_pagamento'], novo_valor_pago,
                baixa_data['juros'], baixa_data['desconto'], lancamento_id
            ))
            
            conn.commit()
            
            # --- LOG ADICIONADO ---
            self.logger.info(f"BAIXA efetuada pelo User ID {self.user_id}. Lançamento ID: {lancamento_id}. Valor: {valor_final_pago:.2f}. Conta ID: {baixa_data['conta_id']}.")
            
            QMessageBox.information(self, "Sucesso", "Lançamento baixado com sucesso!")
            self.load_dashboard_data()
            self.load_lancamentos()
            self.load_extrato() # Recarrega o extrato se a conta estiver selecionada
            
        except Exception as e:
            conn.rollback()
            # --- LOG ADICIONADO ---
            self.logger.error(f"FALHA na baixa (User ID {self.user_id}, Lançamento ID: {lancamento_id}). Erro: {e}", exc_info=True)
            QMessageBox.critical(self, "Erro na Baixa", f"Não foi possível salvar a baixa: {e}")
        finally:
            conn.close()

    def _delete_lancamento(self):
        """Exclui um lançamento (somente se não estiver pago)."""
        lancamento_id, data = self._get_selected_lancamento()
        if not lancamento_id:
            return
            
        if data['status'] == 'PAGO' or (data.get('valor_pago', 0.0) or 0.0) > 0:
            QMessageBox.warning(self, "Ação Inválida", 
                "Não é possível excluir um lançamento que já possui pagamentos.\n"
                "Utilize a função 'Estornar' primeiro.")
            return

        reply = QMessageBox.question(self, "Confirmar Exclusão",
            f"Tem certeza que deseja excluir o lançamento:\n\n"
            f"{data['descricao']}\nValor: R$ {data['valor_previsto']:.2f}",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            
        if reply == QMessageBox.No:
            return
            
        conn = get_connection()
        try:
            cur = conn.cursor()
            conn.execute("BEGIN")
            
            # TODO: Atualizar o valor_total do Título pai
            
            cur.execute("DELETE FROM lancamentos_financeiros WHERE id = ?", (lancamento_id,))
            
            conn.commit()
            
            # --- LOG ADICIONADO ---
            self.logger.info(f"EXCLUSÃO efetuada pelo User ID {self.user_id}. Lançamento ID: {lancamento_id} (Valor: {data['valor_previsto']}).")
            
            QMessageBox.information(self, "Sucesso", "Lançamento excluído.")
            self.load_dashboard_data()
            self.load_lancamentos()

        except Exception as e:
            conn.rollback()
            # --- LOG ADICIONADO ---
            self.logger.error(f"FALHA na exclusão (User ID {self.user_id}, Lançamento ID: {lancamento_id}). Erro: {e}", exc_info=True)
            QMessageBox.critical(self, "Erro", f"Erro ao excluir lançamento: {e}")
        finally:
            conn.close()
            
    def _prompt_estornar_lancamento(self):
        """Verifica e executa o estorno do último pagamento de um lançamento."""
        lancamento_id, data = self._get_selected_lancamento()
        if not lancamento_id:
            return

        if data['status'] == 'PENDENTE' and (data.get('valor_pago', 0.0) or 0.0) == 0:
            QMessageBox.information(self, "Ação Inválida", "Este lançamento não possui nenhuma baixa para estornar.")
            return

        conn = get_connection()
        try:
            cur = conn.cursor()
            # Busca a ÚLTIMA movimentação associada a este lançamento
            cur.execute("""
                SELECT * FROM movimentacoes_contas 
                WHERE lancamento_id = ? 
                ORDER BY id DESC 
                LIMIT 1
            """, (lancamento_id,))
            
            ultima_mov = cur.fetchone()
            
            if not ultima_mov:
                QMessageBox.critical(self, "Erro de Dados", "Lançamento PAGO/PARCIAL não possui movimentação no extrato para estornar.")
                return
                
            conta_nome = self.contas_map.get(ultima_mov['conta_id'], 'Conta Desconhecida')
            
            reply = QMessageBox.question(self, "Confirmar Estorno",
                f"Tem certeza que deseja estornar o último pagamento deste lançamento?\n\n"
                f"Descrição: {ultima_mov['descricao']}\n"
                f"Valor: R$ {ultima_mov['valor']:.2f}\n"
                f"Conta: {conta_nome}",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                
            if reply == QMessageBox.No:
                return
                
            self._execute_estorno(lancamento_id, dict(data), dict(ultima_mov))

        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao preparar estorno: {e}")
        finally:
            conn.close()

    def _execute_estorno(self, lancamento_id, lanc_data, mov_data):
        """Executa a transação de ESTORNO no banco de dados."""
        
        tipo_mov_original = mov_data['tipo_movimento']
        tipo_mov_inverso = 'ENTRADA' if tipo_mov_original == 'SAIDA' else 'SAIDA'
        valor_estorno = mov_data['valor']
        conta_id = mov_data['conta_id']
        
        conn = get_connection()
        try:
            cur = conn.cursor()
            conn.execute("BEGIN")
            
            # 1. Cria a Movimentação INVERSA (Estorno)
            desc_mov = f"ESTORNO ref. Mov. #{mov_data['id']}: {lanc_data['descricao']}"
            cur.execute("""
                INSERT INTO movimentacoes_contas
                (conta_id, lancamento_id, tipo_movimento, valor, data_movimento, descricao, conciliado)
                VALUES (?, ?, ?, ?, DATE('now'), ?, 0)
            """, (
                conta_id, lancamento_id, tipo_mov_inverso,
                valor_estorno, desc_mov
            ))
            
            # 2. Atualiza o Saldo da Conta Financeira (inverso da baixa)
            if tipo_mov_inverso == 'SAIDA':
                cur.execute("UPDATE contas_financeiras SET saldo_atual = saldo_atual - ? WHERE id = ?", 
                            (valor_estorno, conta_id))
            else: # ENTRADA
                cur.execute("UPDATE contas_financeiras SET saldo_atual = saldo_atual + ? WHERE id = ?", 
                            (valor_estorno, conta_id))

            # 3. Atualiza o Lançamento Financeiro
            novo_valor_pago = (lanc_data['valor_pago'] or 0.0) - valor_estorno
            
            # Define o novo status (se o vencimento já passou, volta para VENCIDO)
            hoje = QDate.currentDate().toString("yyyy-MM-dd")
            novo_status = 'PENDENTE'
            if lanc_data['data_vencimento'] < hoje:
                novo_status = 'VENCIDO'
            
            cur.execute("""
                UPDATE lancamentos_financeiros
                SET 
                    status = ?,
                    data_pagamento = (CASE WHEN ? < 0.01 THEN NULL ELSE data_pagamento END),
                    valor_pago = ?
                WHERE id = ?
            """, (
                novo_status, novo_valor_pago, novo_valor_pago, lancamento_id
            ))
            
            conn.commit()
            
            # --- LOG ADICIONADO ---
            self.logger.info(f"ESTORNO efetuado pelo User ID {self.user_id}. Lançamento ID: {lancamento_id}. Valor: {valor_estorno:.2f}. Conta ID: {conta_id}.")
            
            QMessageBox.information(self, "Sucesso", "Estorno realizado com sucesso!")
            self.load_dashboard_data()
            self.load_lancamentos()
            self.load_extrato() # Recarrega o extrato
            
        except Exception as e:
            conn.rollback()
            # --- LOG ADICIONADO ---
            self.logger.error(f"FALHA no estorno (User ID {self.user_id}, Lançamento ID: {lancamento_id}). Erro: {e}", exc_info=True)
            QMessageBox.critical(self, "Erro no Estorno", f"Não foi possível salvar o estorno: {e}")
        finally:
            conn.close()

    def _prompt_edit_lancamento(self):
        """Abre o diálogo de edição para um lançamento PENDENTE."""
        lancamento_id, data = self._get_selected_lancamento()
        if not lancamento_id:
            return
            
        if data['status'] == 'PAGO' or (data.get('valor_pago', 0.0) or 0.0) > 0:
            QMessageBox.warning(self, "Ação Inválida", 
                "Não é possível editar um lançamento que já possui pagamentos (ou está Pago).\n"
                "Utilize a função 'Estornar' primeiro.")
            return
            
        dialog = EditLancamentoDialog(self.user_id, self.empresa_id, data, self)
        
        if dialog.exec_() == QDialog.Accepted:
            edit_data = dialog.get_data()
            if edit_data:
                self._execute_edit(lancamento_id, data['valor_previsto'], edit_data) # Passa o valor antigo
        
    def _execute_edit(self, lancamento_id, valor_antigo, edit_data):
        """Salva as alterações do lançamento e recalcula o título pai."""
        
        conn = get_connection()
        try:
            cur = conn.cursor()
            conn.execute("BEGIN")

            # 1. Atualiza o lançamento
            cur.execute("""
                UPDATE lancamentos_financeiros
                SET 
                    descricao = :descricao,
                    valor_previsto = :valor_previsto,
                    data_vencimento = :data_vencimento,
                    categoria_id = :categoria_id,
                    centro_custo_id = :centro_custo_id
                WHERE id = :id
            """, {
                "id": lancamento_id,
                "descricao": edit_data['descricao'],
                "valor_previsto": edit_data['valor_previsto'],
                "data_vencimento": edit_data['data_vencimento'],
                "categoria_id": edit_data['categoria_id'],
                "centro_custo_id": edit_data['centro_custo_id']
            })
            
            # 2. Recalcula o valor total do Título pai
            # Pega o valor da diferença (novo - antigo) e soma ao total do título
            diferenca_valor = edit_data['valor_previsto'] - valor_antigo
            
            cur.execute("""
                UPDATE titulos_financeiros
                SET valor_total = valor_total + ?
                WHERE id = (
                    SELECT titulo_id FROM lancamentos_financeiros WHERE id = ?
                )
            """, (diferenca_valor, lancamento_id))
            
            conn.commit()
            
            # --- LOG ADICIONADO ---
            self.logger.info(f"EDIÇÃO efetuada pelo User ID {self.user_id}. Lançamento ID: {lancamento_id}. Valor alterado de {valor_antigo} para {edit_data['valor_previsto']}.")
            
            QMessageBox.information(self, "Sucesso", "Lançamento atualizado com sucesso!")
            self.load_dashboard_data()
            self.load_lancamentos()
            
        except Exception as e:
            conn.rollback()
            # --- LOG ADICIONADO ---
            self.logger.error(f"FALHA na edição (User ID {self.user_id}, Lançamento ID: {lancamento_id}). Erro: {e}", exc_info=True)
            QMessageBox.critical(self, "Erro ao Editar", f"Não foi possível salvar as alterações: {e}")
        finally:
            conn.close()

    def _get_selected_movimento(self):
        """Pega o ID da movimentação selecionada na tabela Extrato."""
        row = self.extrato_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Seleção", "Selecione uma movimentação na tabela de extrato primeiro.")
            return None
        
        try:
            mov_id = int(self.extrato_table.item(row, 0).text())
            return mov_id
        except Exception:
            QMessageBox.critical(self, "Erro", "Não foi possível ler o ID da movimentação selecionada.")
            return None

    def _conciliar_movimento(self, conciliar=True):
        """Altera o status 'conciliado' de uma movimentação."""
        mov_id = self._get_selected_movimento()
        if not mov_id:
            return
            
        acao_texto = "conciliar" if conciliar else "desconciliar"
        acao_valor = 1 if conciliar else 0
        
        reply = QMessageBox.question(self, f"Confirmar {acao_texto.capitalize()}",
            f"Tem certeza que deseja {acao_texto} este lançamento?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            
        if reply == QMessageBox.No:
            return
            
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("UPDATE movimentacoes_contas SET conciliado = ? WHERE id = ?", (acao_valor, mov_id))
            conn.commit()
            
            # --- LOG ADICIONADO ---
            self.logger.info(f"CONCILIAÇÃO (User ID {self.user_id}): Movimentação ID: {mov_id} marcada como {acao_texto.upper()}.")
            
            self.load_extrato() # Atualiza a tabela de extrato
            
        except Exception as e:
            conn.rollback()
            # --- LOG ADICIONADO ---
            self.logger.error(f"FALHA na conciliação (User ID {self.user_id}, Mov ID: {mov_id}). Erro: {e}", exc_info=True)
            QMessageBox.critical(self, "Erro de DB", f"Não foi possível {acao_texto} a movimentação: {e}")
        finally:
            conn.close()

    # --- FUNÇÕES DE GRÁFICO (Movidas para o final) ---
    def _setup_graph_styles(self, plot_widget, label_bottom, label_left, horizontal=False):
        """Aplica estilos visuais padrão aos gráficos."""
        plot_widget.setBackground('#fdfdfd')
        plot_widget.showGrid(x=True, y=True, alpha=0.3)
        plot_widget.getAxis('bottom').setTextPen('#555')
        plot_widget.getAxis('left').setTextPen('#555')
        
        styles = {'color':'#555', 'font-size':'13px'}
        plot_widget.setLabel('bottom', label_bottom, **styles)
        plot_widget.setLabel('left', label_left, **styles)
        
        if horizontal:
            plot_widget.getViewBox().invertY(True) # Inverte o eixo Y

    def _load_graph_fluxo_caixa(self, conn):
        """Busca dados e plota o gráfico de Fluxo de Caixa (Receitas vs Despesas)"""
        if not self.graph_fluxo_caixa: return
        self.graph_fluxo_caixa.clear()

        try:
            cur = conn.cursor()
            # Busca Receitas e Despesas agrupadas por dia para os próximos 30 dias
            cur.execute(f"""
                SELECT 
                    data_vencimento,
                    SUM(CASE WHEN tipo = 'A RECEBER' THEN (valor_previsto - IFNULL(valor_pago, 0)) ELSE 0 END) as receitas,
                    SUM(CASE WHEN tipo = 'A PAGAR' THEN (valor_previsto - IFNULL(valor_pago, 0)) ELSE 0 END) as despesas
                FROM lancamentos_financeiros
                WHERE status != 'PAGO'
                  AND data_vencimento BETWEEN DATE('now') AND DATE('now', '+30 days')
                GROUP BY data_vencimento
                ORDER BY data_vencimento
            """)
            
            data = cur.fetchall()
            
            receitas_vals = []
            despesas_vals = []
            ticks = [] # Rótulos do eixo X (Datas)
            
            # Mapeia os dados para os eixos
            for i, row in enumerate(data):
                receitas_vals.append(row['receitas'])
                despesas_vals.append(row['despesas'])
                # Formata a data para (Ex: 14/11)
                ticks.append((i, datetime.strptime(row['data_vencimento'], '%Y-%m-%d').strftime('%d/%m')))
            
            x_axis = self.graph_fluxo_caixa.getAxis('bottom')
            x_axis.setTicks([ticks])
            
            # Barras de Receita (Verde)
            bar_receitas = BarGraphItem(x=range(len(receitas_vals)), height=receitas_vals, width=0.4, brush=(85, 170, 85, 200), name="Receitas")
            # Barras de Despesa (Vermelho) - deslocadas para o lado
            bar_despesas = BarGraphItem(x=[i + 0.4 for i in range(len(despesas_vals))], height=despesas_vals, width=0.4, brush=(200, 85, 85, 200), name="Despesas")
            
            self.graph_fluxo_caixa.addItem(bar_receitas)
            self.graph_fluxo_caixa.addItem(bar_despesas)

        except Exception as e:
            print(f"Erro ao gerar gráfico de fluxo de caixa: {e}")

    def _load_graph_desp_categoria(self, conn):
        """Busca dados e plota o gráfico de Despesas por Categoria (Gráfico de Pizza/Barras)"""
        if not self.graph_desp_categoria: return
        self.graph_desp_categoria.clear()

        try:
            cur = conn.cursor()
            # Busca as 10 maiores categorias de despesa pagas no mês atual
            cur.execute("""
                SELECT 
                    c.nome,
                    SUM(l.valor_pago) as total_pago
                FROM lancamentos_financeiros l
                JOIN categorias_financeiras c ON l.categoria_id = c.id
                WHERE l.tipo = 'A PAGAR' AND l.status = 'PAGO'
                  AND STRFTIME('%Y-%m', l.data_pagamento) = STRFTIME('%Y-%m', 'now')
                GROUP BY c.nome
                ORDER BY total_pago DESC
                LIMIT 10
            """)
            
            data = cur.fetchall()
            
            valores = [row['total_pago'] for row in data]
            nomes = [row['nome'] for row in data]
            ticks = [(i, nome) for i, nome in enumerate(nomes)] # Rótulos do eixo Y
            
            y_axis = self.graph_desp_categoria.getAxis('left')
            y_axis.setTicks([ticks])
            
            # Gradiente de cor para as barras
            colors = []
            base_color = QColor(220, 0, 0)
            for i in range(len(valores)):
                alpha = 255 - (i * (150 // max(1, len(valores)-1))) if len(valores) > 1 else 255
                colors.append((base_color.red(), base_color.green(), base_color.blue(), alpha))
            
            # Gráfico de barras horizontal
            bar_item = BarGraphItem(y=range(len(valores)), height=0.7, width=valores, brushes=colors)
            
            self.graph_desp_categoria.addItem(bar_item)
            
        except Exception as e:
            print(f"Erro ao gerar gráfico de despesas: {e}")