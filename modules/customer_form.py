# modules/customer_form.py
import sqlite3
import requests
import json
from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, 
    QMessageBox, QGridLayout, QFrame, QTabWidget, QTableWidget, 
    QHeaderView, QTableWidgetItem, QAbstractItemView, QDialog,
    QStackedWidget, QComboBox # <-- As importações que faltavam
)
from PyQt5.QtCore import Qt, pyqtSignal
from database.db import get_connection

class CustomerForm(QWidget):
    # Sinal emitido quando um cliente é salvo (para o PDV)
    customer_saved = pyqtSignal(int, str) # id, nome

    def __init__(self, user_id, start_cpf=None, start_cnpj=None, parent=None):
        super().__init__()
        
        # --- API TOKEN ---
        self.API_TOKEN = "22896|Bxa6LMJ6uAIerPz7pxBcjmKNxMCUFiZn" 
        
        self.user_id = user_id
        self.current_customer_id = None
        self.setWindowTitle("Cadastro de Clientes")
        
        self._load_field_permissions()
        self._setup_styles()
        self._build_ui()
        self._connect_signals()
        self._apply_field_permissions()
        
        self.set_mode(0) 
        
        if start_cpf or start_cnpj:
            self.show_new_customer_form()
            if start_cpf:
                self.cpf.setText(start_cpf)
            if start_cnpj:
                self.cnpj.setText(start_cnpj)
            self.nome_razao.setFocus()

    def _setup_styles(self):
        self.setStyleSheet("""
            QWidget { background-color: #f8f8fb; font-family: 'Segoe UI'; }
            QLabel { font-weight: bold; color: #444; }
            QLabel.required::after { content: " *"; color: #e74c3c; }
            
            /* Tabela de Busca */
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
            
            /* Painel de Cadastro */
            QFrame#form_panel {
                background-color: #fdfdfd;
                border: 1px solid #c0c0d0;
                border-radius: 8px;
            }
            QLabel#form_title {
                font-size: 16px; font-weight: bold; color: #005fa3;
                padding: 5px; border-bottom: 1px solid #eee;
            }
            
            QTabWidget::pane { border-top: 1px solid #c0c0d0; background: #fdfdfd; }
            QTabBar::tab { background: #e0e0e0; padding: 8px 20px; }
            QTabBar::tab:selected { background: #fdfdfd; border: 1px solid #c0c0d0; border-bottom: none; }
            
            QLineEdit, QTextEdit, QComboBox {
                border: 1px solid #c0c0d0; border-radius: 5px; 
                padding: 6px; background-color: white;
            }
            QLineEdit:readOnly { background-color: #e0e0e0; }
            
            QPushButton {
                background-color: #0078d7; color: white; border-radius: 6px;
                padding: 8px 15px; font-weight: bold;
            }
            QPushButton:hover { background-color: #005fa3; }
            
            /* Estilo do novo botão de busca */
            QPushButton#btn_buscar_doc {
                background-color: #2ECC71; /* Verde */
                font-size: 12px;
                padding: 6px 10px;
                max-width: 100px;
            }
            QPushButton#btn_buscar_doc:hover { background-color: #27AE60; }
        """)

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        
        # --- 1. PAINEL DE BUSCA E NAVEGAÇÃO ---
        self.search_panel = QWidget()
        search_layout = QHBoxLayout(self.search_panel)
        search_layout.setContentsMargins(0, 10, 0, 10)
        self.btn_novo_cliente_top = QPushButton("Novo Cliente")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Pesquisar por nome ou CPF/CNPJ...")
        self.btn_pesquisar = QPushButton("Pesquisar")
        
        search_layout.addWidget(self.btn_novo_cliente_top)
        search_layout.addWidget(self.search_input, 1) # Expande
        search_layout.addWidget(self.btn_pesquisar)
        
        # --- 2. STACKED WIDGET (Tabela / Formulário) ---
        self.stack = QStackedWidget()
        
        # --- Tela 0: Tabela de Clientes ---
        self.table_widget = QWidget()
        table_layout = QVBoxLayout(self.table_widget)
        table_layout.setContentsMargins(0,0,0,0)
        self.customer_table = QTableWidget()
        self.customer_table.setColumnCount(4)
        self.customer_table.setHorizontalHeaderLabels(["ID", "Nome/Razão Social", "CPF/CNPJ", "Telefone"])
        self.customer_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.customer_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.customer_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.customer_table.setColumnHidden(0, True)
        table_layout.addWidget(self.customer_table)
        
        # --- Tela 1: Formulário de Cadastro ---
        self.form_panel = QFrame()
        self.form_panel.setObjectName("form_panel")
        form_layout = QVBoxLayout(self.form_panel)
        form_layout.addWidget(QLabel("Cadastro de Cliente", objectName="form_title"))
        
        # --- Campos (definidos para acesso) ---
        self.nome_razao = QLineEdit()
        self.tipo_cadastro = QComboBox()
        self.tipo_cadastro.addItems(["Cliente", "Fornecedor", "Ambos"])
        self.categoria = QLineEdit("Padrão")
        self.cpf = QLineEdit()
        self.rg = QLineEdit()
        self.cnpj = QLineEdit()
        self.data_nascimento = QLineEdit()
        self.celular = QLineEdit()
        self.email = QLineEdit()
        self.telefone_residencial = QLineEdit()
        self.cep = QLineEdit()
        self.cep.setMaxLength(9)
        self.endereco = QLineEdit()
        self.numero = QLineEdit()
        self.complemento = QLineEdit()
        self.bairro = QLineEdit()
        self.municipio = QLineEdit()
        self.uf = QLineEdit()
        self.uf.setMaxLength(2)
        
        self.btn_buscar_doc = QPushButton("Buscar Dados")
        self.btn_buscar_doc.setObjectName("btn_buscar_doc")

        # Abas
        self.tabs = QTabWidget()
        tab_geral = QWidget()
        tab_endereco = QWidget()
        self.tabs.addTab(tab_geral, "Geral")
        self.tabs.addTab(tab_endereco, "Endereço")
        
        # --- Layout Aba "Geral" (ATUALIZADO) ---
        geral_layout = QGridLayout(tab_geral)
        geral_layout.addWidget(QLabel("Nome/Razão Social: *", objectName="required"), 0, 0)
        geral_layout.addWidget(self.nome_razao, 0, 1, 1, 5)

        geral_layout.addWidget(QLabel("Tipo:"), 1, 0)
        geral_layout.addWidget(self.tipo_cadastro, 1, 1)
        geral_layout.addWidget(QLabel("Categoria:"), 1, 2)
        geral_layout.addWidget(self.categoria, 1, 3)

        geral_layout.addWidget(QLabel("CPF:"), 2, 0)
        geral_layout.addWidget(self.cpf, 2, 1)
        geral_layout.addWidget(QLabel("RG:"), 2, 2)
        geral_layout.addWidget(self.rg, 2, 3)
        
        geral_layout.addWidget(QLabel("CNPJ:"), 3, 0)
        
        cnpj_layout = QHBoxLayout()
        cnpj_layout.setContentsMargins(0,0,0,0)
        cnpj_layout.addWidget(self.cnpj) 
        cnpj_layout.addWidget(self.btn_buscar_doc) 
        geral_layout.addLayout(cnpj_layout, 3, 1) 
        
        geral_layout.addWidget(QLabel("Data Nascimento:"), 3, 2)
        geral_layout.addWidget(self.data_nascimento, 3, 3)

        geral_layout.setColumnStretch(4, 1) # Stretch

        # Linha separadora
        line = QFrame(); line.setFrameShape(QFrame.HLine); line.setFrameShadow(QFrame.Sunken)
        geral_layout.addWidget(line, 4, 0, 1, 6)

        # Seção de Contatos
        geral_layout.addWidget(QLabel("Contatos*", objectName="required"), 5, 0, Qt.AlignTop)
        geral_layout.addWidget(QLabel("Celular:"), 6, 0)
        geral_layout.addWidget(self.celular, 6, 1)
        geral_layout.addWidget(QLabel("Email:"), 7, 0)
        geral_layout.addWidget(self.email, 7, 1, 1, 3)
        geral_layout.addWidget(QLabel("Residencial:"), 8, 0)
        geral_layout.addWidget(self.telefone_residencial, 8, 1)
        
        geral_layout.setRowStretch(9, 1) # Stretch no final

        # Layout Aba "Endereço"
        end_layout = QGridLayout(tab_endereco)
        cep_layout = QHBoxLayout()
        cep_layout.addWidget(self.cep)
        self.btn_buscar_cep = QPushButton("Buscar CEP")
        cep_layout.addWidget(self.btn_buscar_cep)
        end_layout.addWidget(QLabel("CEP:"), 0, 0)
        end_layout.addLayout(cep_layout, 0, 1)
        end_layout.addWidget(QLabel("Endereço:"), 1, 0)
        end_layout.addWidget(self.endereco, 1, 1, 1, 3)
        end_layout.addWidget(QLabel("Nº:"), 2, 0)
        end_layout.addWidget(self.numero, 2, 1)
        end_layout.addWidget(QLabel("Bairro:"), 3, 0)
        end_layout.addWidget(self.bairro, 3, 1)
        end_layout.addWidget(QLabel("Complemento:"), 3, 2)
        end_layout.addWidget(self.complemento, 3, 3)
        end_layout.addWidget(QLabel("Município:"), 4, 0)
        end_layout.addWidget(self.municipio, 4, 1)
        end_layout.addWidget(QLabel("UF:"), 4, 2)
        end_layout.addWidget(self.uf, 4, 3)
        end_layout.setRowStretch(5, 1); end_layout.setColumnStretch(4, 1)
        
        form_layout.addWidget(self.tabs)
        
        # Botões do formulário
        form_btn_layout = QHBoxLayout()
        form_btn_layout.addStretch()
        self.btn_salvar = QPushButton("Salvar")
        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.setStyleSheet("background-color: #95A5A6;")
        form_btn_layout.addWidget(self.btn_cancelar)
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
            self.load_customers()
        else:
            self.stack.setCurrentIndex(1)
            self.search_panel.setVisible(False)

    def _connect_signals(self):
        self.btn_novo_cliente_top.clicked.connect(self.show_new_customer_form)
        self.btn_salvar.clicked.connect(self.save_customer)
        self.btn_cancelar.clicked.connect(self.cancel_action)
        self.btn_buscar_cep.clicked.connect(self.search_cep)
        self.btn_pesquisar.clicked.connect(self.load_customers)
        self.search_input.returnPressed.connect(self.load_customers)
        self.customer_table.itemDoubleClicked.connect(self._load_customer_for_edit)
        self.btn_buscar_doc.clicked.connect(self.search_document)

    def _load_customer_for_edit(self, item):
        """Carrega os dados de um cliente da tabela para o formulário."""
        row = item.row()
        customer_id_str = self.customer_table.item(row, 0).text()
        if not customer_id_str:
            return
            
        customer_id = int(customer_id_str)
        if customer_id == 1: 
            QMessageBox.warning(self, "Ação Inválida", "O 'CONSUMIDOR FINAL' não pode ser editado.")
            return

        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM clientes WHERE id = ?", (customer_id,))
            data = cur.fetchone()
            if not data:
                QMessageBox.critical(self, "Erro", "Cliente não encontrado no banco de dados.")
                return

            self.current_customer_id = customer_id
            self.nome_razao.setText(data['nome_razao'])
            self.tipo_cadastro.setCurrentText(data['tipo_cadastro'] or "Cliente")
            self.categoria.setText(data['categoria'] or "Padrão")
            self.cpf.setText(data['cpf'])
            self.rg.setText(data['rg'])
            self.cnpj.setText(data['cnpj'])
            self.data_nascimento.setText(data['data_nascimento'])
            self.celular.setText(data['celular'])
            self.email.setText(data['email'])
            self.telefone_residencial.setText(data['telefone_residencial'])
            self.cep.setText(data['cep'])
            self.endereco.setText(data['endereco'])
            self.numero.setText(data['numero'])
            self.complemento.setText(data['complemento'])
            self.bairro.setText(data['bairro'])
            self.municipio.setText(data['municipio'])
            self.uf.setText(data['uf'])

            self.set_mode(1) 

        except Exception as e:
            QMessageBox.critical(self, "Erro ao Carregar", f"Não foi possível carregar o cliente: {e}")
        finally:
            conn.close()

    def show_new_customer_form(self):
        self.clear_form()
        self.set_mode(1)
        self.nome_razao.setFocus()

    def cancel_action(self):
        if self.parent() and isinstance(self.parent(), QDialog):
            self.parent().reject()
        else:
            self.clear_form()
            self.set_mode(0)

    def search_cep(self):
        cep = self.cep.text().strip().replace("-", "")
        if len(cep) != 8:
            QMessageBox.warning(self, "CEP Inválido", "O CEP deve conter 8 dígitos.")
            return
        try:
            response = requests.get(f"https://viacep.com.br/ws/{cep}/json/")
            response.raise_for_status()
            data = response.json()
            if data.get("erro"):
                QMessageBox.warning(self, "Erro", "CEP não encontrado.")
            else:
                self.endereco.setText(data.get("logradouro", ""))
                self.bairro.setText(data.get("bairro", ""))
                self.municipio.setText(data.get("localidade", ""))
                self.uf.setText(data.get("uf", ""))
                self.numero.setFocus()
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Erro de Rede", f"Não foi possível consultar o CEP: {e}")

    def clear_form(self):
        self.current_customer_id = None
        self.nome_razao.clear()
        self.tipo_cadastro.setCurrentIndex(0) 
        self.categoria.setText("Padrão")
        self.cpf.clear()
        self.rg.clear()
        self.cnpj.clear()
        self.data_nascimento.clear()
        self.celular.clear()
        self.email.clear()
        self.telefone_residencial.clear()
        self.cep.clear()
        self.endereco.clear()
        self.numero.clear()
        self.complemento.clear()
        self.bairro.clear()
        self.municipio.clear()
        self.uf.clear()
        self.nome_razao.setFocus()

    def _validate_fields(self):
        """Verifica se os campos obrigatórios estão preenchidos."""
        if not self.nome_razao.text(): return False, "Nome/Razão Social"
        if not self.cpf.text() and not self.cnpj.text(): return False, "CPF ou CNPJ"
        if not self.tipo_cadastro.currentText(): return False, "Tipo"
        if not self.categoria.text(): return False, "Categoria"
        return True, ""

    def save_customer(self):
        valido, campo = self._validate_fields()
        if not valido:
            QMessageBox.warning(self, "Campo Obrigatório", f"O campo '{campo}' é obrigatório.")
            return

        data = {
            "nome_razao": self.nome_razao.text(),
            "tipo_cadastro": self.tipo_cadastro.currentText(),
            "categoria": self.categoria.text(),
            "cpf": self.cpf.text(),
            "rg": self.rg.text(),
            "cnpj": self.cnpj.text(),
            "data_nascimento": self.data_nascimento.text(),
            "celular": self.celular.text(),
            "email": self.email.text(),
            "telefone_residencial": self.telefone_residencial.text(),
            "cep": self.cep.text(),
            "endereco": self.endereco.text(),
            "numero": self.numero.text(),
            "complemento": self.complemento.text(),
            "bairro": self.bairro.text(),
            "municipio": self.municipio.text(),
            "uf": self.uf.text(),
        }

        conn = get_connection()
        try:
            cur = conn.cursor()
            
            if self.current_customer_id:
                fields = data.keys()
                values = list(data.values())
                values.append(self.current_customer_id)
                set_clause = ", ".join([f"{field} = ?" for field in fields])
                query = f"UPDATE clientes SET {set_clause} WHERE id = ?"
                cur.execute(query, tuple(values))
                msg = "Cliente atualizado com sucesso!"
                
            else:
                fields = tuple(data.keys())
                placeholders = tuple(["?"] * len(fields))
                values = tuple(data.values())
                query = f"INSERT INTO clientes ({', '.join(fields)}) VALUES ({','.join(placeholders)})"
                cur.execute(query, values)
                self.current_customer_id = cur.lastrowid
                msg = "Cliente salvo com sucesso!"
            
            conn.commit()
            QMessageBox.information(self, "Sucesso", msg)
            
            if self.parent() and isinstance(self.parent(), QDialog):
                self.customer_saved.emit(self.current_customer_id, self.nome_razao.text())
                self.parent().accept()
            else:
                self.set_mode(0)
                self.clear_form() 

        except sqlite3.IntegrityError:
            QMessageBox.critical(self, "Erro", "Este CPF/CNPJ já existe no banco de dados.")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao salvar cliente: {e}")
        finally:
            conn.close()
            
    def load_customers(self):
        """Carrega/Busca clientes e preenche a tabela."""
        self.customer_table.setRowCount(0)
        search_term = self.search_input.text().strip()
        conn = get_connection()
        try:
            cur = conn.cursor()
            query = "SELECT id, nome_razao, cpf, cnpj, celular FROM clientes WHERE id > 1" 
            params = []
            
            if search_term:
                query += " AND (nome_razao LIKE ? OR cpf LIKE ? OR cnpj LIKE ?)"
                params.extend([f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"])
            
            query += " ORDER BY nome_razao"
            cur.execute(query, tuple(params))
            
            clientes = cur.fetchall()
            for cliente in clientes:
                row = self.customer_table.rowCount()
                self.customer_table.insertRow(row)
                cpf_cnpj = cliente['cpf'] if cliente['cpf'] else cliente['cnpj']
                self.customer_table.setItem(row, 0, QTableWidgetItem(str(cliente['id'])))
                self.customer_table.setItem(row, 1, QTableWidgetItem(cliente['nome_razao']))
                self.customer_table.setItem(row, 2, QTableWidgetItem(cpf_cnpj))
                self.customer_table.setItem(row, 3, QTableWidgetItem(cliente['celular']))
        
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao carregar clientes: {e}")
        finally:
            conn.close()

    def _load_field_permissions(self):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT campos FROM permissoes WHERE user_id = ?", (self.user_id,))
            perms = cur.fetchone()
            if perms and perms['campos']:
                all_perms = json.loads(perms['campos'])
                # ATUALIZADO para usar 'form_customer' (do permissions.py)
                self.user_field_permissions = all_perms.get('form_customer', {})
        except Exception:
            self.setEnabled(False)
        finally:
            conn.close()

    def _apply_field_permissions(self):
        if not self.user_field_permissions.get("btn_salvar", "Total") == "Total":
            self.btn_salvar.setEnabled(False)
            self.btn_novo_cliente_top.setEnabled(False)

    # --- MÉTODOS ATUALIZADOS PARA A API INVERTEXTO ---

    def search_document(self):
        """Verifica se CNPJ ou CPF estão preenchidos e inicia a busca."""
        if self.API_TOKEN == "COLE_SEU_TOKEN_AQUI":
            QMessageBox.critical(self, "Erro de API", 
                "O Token da API 'invertexto' não foi configurado no arquivo 'customer_form.py'.")
            return
            
        cnpj = self.cnpj.text().strip().replace(".", "").replace("/", "").replace("-", "")
        cpf = self.cpf.text().strip().replace(".", "").replace("-", "")

        if cnpj:
            self._search_cnpj(cnpj)
        elif cpf:
            QMessageBox.information(self, "Busca de CPF", 
                "A busca automática de dados por CPF não é permitida por motivos legais (LGPD).\n"
                "Apenas a busca por CNPJ (dados públicos) está disponível.")
        else:
            QMessageBox.warning(self, "Campo Vazio", "Digite um CNPJ no campo 'CNPJ' para buscar os dados.")

    def _search_cnpj(self, cnpj):
        """Executa a busca do CNPJ na API invertexto."""
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
            end = data.get("endereco", {}).get("logradouro", "")
            num = data.get("endereco", {}).get("numero", "")
            
            confirm_text = (
                f"<b>Empresa Encontrada:</b>\n"
                f"<b>Razão Social:</b> {nome}\n"
                f"<b>Nome Fantasia:</b> {fantasia}\n"
                f"<b>Endereço:</b> {end}, {num}\n\n"
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
        
        self.nome_razao.setText(data.get("razao_social", ""))
        
        # Auto-seleciona "Fornecedor"
        if self.tipo_cadastro.currentText() == "Cliente":
            self.tipo_cadastro.setCurrentText("Fornecedor")

        # Endereço
        end = data.get("endereco", {})
        self.cep.setText(end.get("cep", "").replace(".", ""))
        self.endereco.setText(end.get("logradouro", ""))
        self.numero.setText(end.get("numero", ""))
        self.complemento.setText(end.get("complemento", ""))
        self.bairro.setText(end.get("bairro", ""))
        self.municipio.setText(end.get("cidade", ""))
        self.uf.setText(end.get("uf", ""))
        
        self.cpf.clear()
             
        self.email.setText(data.get("email", ""))
        self.celular.setText(data.get("telefone", ""))
        
        # Foca na próxima aba
        self.tabs.setCurrentIndex(1)
        self.numero.setFocus()