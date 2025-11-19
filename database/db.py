# -*- coding: utf-8 -*-
# database/db.py
import sqlite3
import os
import json
import sys
import uuid
from datetime import datetime
from config.permissions import PERMISSION_SCHEMA

# Nome padrão do banco
DEFAULT_DB_NAME = "bluesys.db"

# --- FUNÇÕES PARA GERENCIAR CAMINHOS (CORREÇÃO DO EXECUTÁVEL) ---
def get_base_dir():
    """Retorna o diretório onde o .exe está, ou o diretório do script .py"""
    if getattr(sys, 'frozen', False):
        # Se for .exe, pega a pasta onde o .exe está
        return os.path.dirname(sys.executable)
    # Se for .py, pega a pasta do projeto
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BASE_DIR = get_base_dir()
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")

def load_settings():
    """Carrega configurações de conexão (para rede)."""
    default_settings = {
        "db_path": os.path.join(BASE_DIR, "database", DEFAULT_DB_NAME)
    }
    
    # Se não existir settings.json, cria um padrão
    if not os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(default_settings, f, indent=4)
        except Exception: pass
            
    try:
        with open(SETTINGS_FILE, 'r') as f:
            settings = json.load(f)
            if "db_path" not in settings:
                settings["db_path"] = default_settings["db_path"]
            return settings
    except Exception:
        return default_settings

def get_connection():
    """Conecta ao banco definido no settings.json"""
    settings = load_settings()
    db_path = settings["db_path"]
    
    # Tenta criar o diretório se não existir (apenas para SQLite local)
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        try: os.makedirs(db_dir, exist_ok=True)
        except OSError: pass

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row 
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

# --- FUNÇÃO PARA POPULAR DADOS INICIAIS ---
def populate_initial_data(cursor):
    """
    Popula o banco de dados com dados essenciais na primeira execução.
    """
    # 1. Categorias Padrão
    cursor.execute("SELECT id FROM categorias LIMIT 1")
    if not cursor.fetchone():
        print("Populando árvore de classes padrão...")
        categorias_tree = [
            (1, 1, 'Produtos para Revenda', None, 0),
            (2, 1, 'Acessorio', 1, 1),
            (3, 1, 'Alimentos', 1, 1),
            (4, 1, 'Bebidas', 1, 1),
            (5, 1, 'Bijuterias', 1, 1),
            (6, 1, 'Brinquedos', 1, 1),
            (7, 1, 'Cama Mesa Banho', 1, 1),
            (8, 1, 'Conveniencia', 1, 1),
            (9, 1, 'Decoracao', 1, 1),
            (10, 1, 'Diversos', 1, 1),
            (11, 1, 'Estacionamento', 1, 1),
            (12, 1, 'Fantasia', 1, 1),
            (13, 1, 'Flores', 1, 1),
            (14, 1, 'Kits', 1, 1),
            (15, 1, 'Leds', 1, 1),
            (16, 1, 'Loja', 1, 1),
            (17, 1, 'Maquiagem', 1, 1),
            (18, 1, 'Natal', 1, 1),
            (19, 1, 'Papelaria', 1, 1),
            (20, 1, 'Perfumaria', 1, 1),
            (21, 1, 'Uso e Consumo', 1, 1),
            (22, 1, 'Utensilios', 1, 1),
            (23, 1, 'Utilidades', 1, 1),
            (24, 1, 'Variedades', 1, 1),
            (25, 1, 'Vestuario', 1, 1),
            (26, 1, 'Produtos Private Label', 1, 1),
            (27, 1, 'Receitas', 1, 1),
            (28, 1, 'Recursos de Terceiros', 1, 1),
            (29, 1, 'Recursos Fiscais', 1, 1),
            (30, 1, 'Serviços', 1, 1),
            (31, 1, 'Tabelas', 1, 1),
        ]
        try:
            cursor.executemany("""
                INSERT INTO categorias (id, empresa_id, name, parent_id, level) 
                VALUES (?, ?, ?, ?, ?)
            """, categorias_tree)
        except Exception as e:
            print(f"Erro ao inserir categorias: {e}")

    # 2. Dados Essenciais de Configuração
    try:
        cursor.execute("SELECT id FROM empresas WHERE id = 1")
        if cursor.fetchone():
             # Garante tabela de preço e depósito padrão
             cursor.execute("""
                 INSERT OR IGNORE INTO tabelas_preco (id, nome_tabela, identificador_loja, descricao, active) 
                 VALUES (1, 'Tabela Padrão Venda', '00.000.000/0001-00', 'Lista principal de venda (Matriz)', 1)
             """)
             cursor.execute("""
                 INSERT OR IGNORE INTO depositos (id, empresa_id, nome, codigo) 
                 VALUES (1, 1, 'Estoque Principal', 'EST-01')
             """)
        
        # Garante sequência de código interno
        cursor.execute("SELECT MAX(valor) FROM sequencias WHERE nome = 'COD_INTERNO'")
        if cursor.fetchone()[0] is None:
            cursor.execute("INSERT INTO sequencias (nome, valor, prefixo) VALUES ('COD_INTERNO', 203000, '')")

        # 3. Motivos de Cancelamento (NOVO)
        motivos = [
            ("Erro de Digitação", 1),
            ("Desistência do Cliente", 1),
            ("Troca de Produto", 1),
            ("Erro no Preço", 1),
            ("Forma de Pagamento Recusada", 1),
            ("Produto com Defeito", 1)
        ]
        cursor.executemany("""
            INSERT OR IGNORE INTO motivos_cancelamento (descricao, ativo) VALUES (?, ?)
        """, motivos)
        
    except Exception as e:
        print(f"Erro ao popular dados iniciais: {e}")

def create_tables():
    """Cria as tabelas necessárias se não existirem."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # --- DEFINIÇÃO DAS COLUNAS DE SINCRONIZAÇÃO (PREPARAÇÃO PARA NUVEM) ---
    sync_cols = """
        uuid TEXT UNIQUE,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        sync_status INTEGER DEFAULT 0,
        is_deleted INTEGER DEFAULT 0
    """

    # --- 1. GESTÃO ---
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_text TEXT NOT NULL, is_active INTEGER DEFAULT 1,
            theme_name TEXT DEFAULT 'Azul', theme_color TEXT DEFAULT '#0078d7',
            {sync_cols}
        )
    """)
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS permissoes (
            user_id INTEGER UNIQUE NOT NULL,
            modulos TEXT, formularios TEXT, campos TEXT, limites TEXT,
            FOREIGN KEY (user_id) REFERENCES usuarios (id) ON DELETE CASCADE,
            {sync_cols}
        )
    """)
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_razao TEXT NOT NULL,
            tipo_cadastro TEXT DEFAULT 'Cliente', 
            categoria TEXT DEFAULT 'Padrão',   
            cpf TEXT, rg TEXT, cnpj TEXT, data_nascimento TEXT,
            celular TEXT, email TEXT, telefone_residencial TEXT,
            cep TEXT, endereco TEXT, numero TEXT, complemento TEXT,
            bairro TEXT, municipio TEXT, uf TEXT,
            data_cadastro TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(cpf, cnpj),
            {sync_cols}
        )
    """)
    # Garante consumidor final
    cursor.execute("INSERT OR IGNORE INTO clientes (id, nome_razao, cpf) VALUES (1, 'CONSUMIDOR FINAL', '000.000.000-00')")

    # --- 2. CONFIGURAÇÃO ---
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS empresas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            razao_social TEXT NOT NULL, nome_fantasia TEXT, cnpj TEXT UNIQUE NOT NULL,
            inscricao_estadual TEXT, inscricao_municipal TEXT, regime_tributario INTEGER, crt INTEGER,
            end_logradouro TEXT, end_numero TEXT, end_complemento TEXT, end_bairro TEXT, end_cep TEXT, end_municipio TEXT, end_uf TEXT,
            telefone TEXT, email TEXT, responsavel_legal TEXT, cpf_responsavel TEXT,
            certificado_path TEXT, certificado_senha TEXT, certificado_validade DATE, 
            notificar_venc_cert BOOLEAN DEFAULT 0, notificar_venc_dias INTEGER DEFAULT 30,
            csc TEXT, csc_id TEXT, csc_validade TEXT,
            ambiente INTEGER DEFAULT 2, status INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            {sync_cols}
        )
    """)
    cursor.execute("INSERT OR IGNORE INTO empresas (id, razao_social, nome_fantasia, cnpj) VALUES (1, 'MINHA EMPRESA (PADRAO)', 'EMPRESA MODELO', '00.000.000/0001-00')")

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS locais_escrituracao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL REFERENCES empresas(id),
            nome_local TEXT NOT NULL, codigo_interno TEXT, cnpj TEXT, inscricao_estadual TEXT,
            end_logradouro TEXT, end_numero TEXT, end_complemento TEXT, end_bairro TEXT, end_cep TEXT, end_municipio TEXT, end_uf TEXT,
            responsavel_operacional TEXT, tipo_local INTEGER, herdar_config_empresa BOOLEAN DEFAULT 1,
            ambiente INTEGER, certificado_path TEXT, certificado_senha TEXT, certificado_validade DATE,
            notificar_venc_cert BOOLEAN DEFAULT 0, notificar_venc_dias INTEGER DEFAULT 30,
            csc TEXT, csc_id TEXT, csc_validade TEXT,
            status INTEGER DEFAULT 1, data_cadastro TEXT DEFAULT CURRENT_TIMESTAMP,
            {sync_cols}
        )
    """)

    # --- 3. TERMINAIS E VENDAS ---
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS terminais_pdv (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL REFERENCES empresas(id),
            local_id INTEGER NOT NULL REFERENCES locais_escrituracao(id),
            nome_terminal TEXT NOT NULL, hostname TEXT UNIQUE, codigo_interno VARCHAR(50),
            tipo_terminal INTEGER DEFAULT 1, modo_operacao INTEGER DEFAULT 1,
            serie_fiscal INTEGER, numero_nfe_atual INTEGER DEFAULT 0,
            impressora_nome TEXT, impressora_modelo TEXT, impressora_tipo_conexao INTEGER, 
            impressora_endereco_conexao TEXT, impressora_largura_papel INTEGER DEFAULT 80, impressora_modo_impressao INTEGER DEFAULT 1,
            servidor_pre_venda TEXT, ambiente INTEGER DEFAULT 2, csc TEXT, csc_id TEXT, certificado_path TEXT, 
            status INTEGER DEFAULT 1, habilita_nao_fiscal BOOLEAN DEFAULT 1,
            
            conta_financeira_id INTEGER REFERENCES contas_financeiras(id),
            conta_destino_dinheiro_id INTEGER REFERENCES contas_financeiras(id),
            conta_destino_cartao_id INTEGER REFERENCES contas_financeiras(id),
            conta_destino_pix_id INTEGER REFERENCES contas_financeiras(id),
            conta_destino_outros_id INTEGER REFERENCES contas_financeiras(id),
            
            price_list_id_padrao INTEGER, deposito_id_padrao INTEGER,
            data_cadastro TEXT DEFAULT CURRENT_TIMESTAMP,
            {sync_cols}
        )
    """)
    
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS caixa_sessoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL, terminal_id INTEGER, 
            data_abertura TEXT DEFAULT CURRENT_TIMESTAMP, data_fechamento TEXT, 
            valor_inicial REAL NOT NULL, valor_final_calculado REAL, valor_final_informado REAL,
            diferenca REAL, autorizador_id INTEGER, status TEXT DEFAULT 'ABERTO',
            FOREIGN KEY (user_id) REFERENCES usuarios (id),
            FOREIGN KEY (terminal_id) REFERENCES terminais_pdv (id),
            {sync_cols}
        )
    """)
    
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS vendas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, cliente_id INTEGER DEFAULT 1, caixa_id INTEGER,
            empresa_id INTEGER, local_id INTEGER, terminal_id INTEGER, 
            numero_venda_terminal INTEGER, data_venda TEXT DEFAULT CURRENT_TIMESTAMP,
            subtotal REAL NOT NULL, desconto_itens REAL DEFAULT 0.0, desconto_geral REAL DEFAULT 0.0, 
            total_final REAL NOT NULL, total_pago REAL NOT NULL, troco REAL DEFAULT 0.0,
            status TEXT DEFAULT 'FINALIZADA', prevenda_origem_id INTEGER, tipo_documento TEXT DEFAULT 'FISCAL',
            FOREIGN KEY (user_id) REFERENCES usuarios (id),
            FOREIGN KEY (cliente_id) REFERENCES clientes (id),
            FOREIGN KEY (caixa_id) REFERENCES caixa_sessoes (id),
            FOREIGN KEY (empresa_id) REFERENCES empresas (id),
            FOREIGN KEY (local_id) REFERENCES locais_escrituracao (id),
            FOREIGN KEY (terminal_id) REFERENCES terminais_pdv (id),
            {sync_cols}
        )
    """)
    
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS vendas_itens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venda_id INTEGER NOT NULL, produto_id INTEGER, 
            codigo_barras TEXT NOT NULL, descricao TEXT NOT NULL, 
            quantidade REAL NOT NULL, preco_unitario REAL NOT NULL, 
            desconto_item REAL DEFAULT 0.0, total_item REAL NOT NULL,
            sku_id INTEGER,
            FOREIGN KEY (venda_id) REFERENCES vendas (id) ON DELETE CASCADE,
            {sync_cols}
        )
    """)
    
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS vendas_pagamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venda_id INTEGER NOT NULL, forma TEXT NOT NULL, valor REAL NOT NULL,
            tipo_pagamento TEXT, tipo_cartao TEXT, parcelas INTEGER DEFAULT 1,  
            nsu TEXT, doc TEXT,                    
            FOREIGN KEY (venda_id) REFERENCES vendas (id) ON DELETE CASCADE,
            {sync_cols}
        )
    """)
    
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS caixa_movimentacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            caixa_id INTEGER NOT NULL, user_id INTEGER NOT NULL, terminal_id INTEGER NOT NULL,
            tipo TEXT NOT NULL, valor REAL NOT NULL, motivo TEXT, autorizador_id INTEGER,
            data_movimento TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (caixa_id) REFERENCES caixa_sessoes (id),
            {sync_cols}
        )
    """)
    
    # --- 4. PRODUTOS ---
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS categorias (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          empresa_id INT REFERENCES empresas(id),
          name VARCHAR(200) NOT NULL, code VARCHAR(50),
          parent_id INT REFERENCES categorias(id),
          path TEXT, level SMALLINT DEFAULT 0, active BOOLEAN DEFAULT TRUE,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          {sync_cols}
        )
    """)

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS produtos (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          empresa_id INT REFERENCES empresas(id),
          nome VARCHAR(255) NOT NULL, descricao TEXT, tipo VARCHAR(50), 
          marca VARCHAR(100), modelo VARCHAR(100),
          categoria_id INT REFERENCES categorias(id),
          active BOOLEAN DEFAULT TRUE,
          codigo_interno VARCHAR UNIQUE, ean VARCHAR, unidade VARCHAR, peso_kg REAL,
          id_fornecedor INT REFERENCES fornecedores(id),
          
          data_validade DATE,
          caminho_imagem TEXT,
          {sync_cols}
        )
    """)
    
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS tabelas_preco (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          nome_tabela VARCHAR NOT NULL, identificador_loja VARCHAR NOT NULL,
          descricao TEXT, active BOOLEAN DEFAULT TRUE,
          UNIQUE(nome_tabela, identificador_loja),
          {sync_cols}
        )
    """)

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS produto_tabela_preco (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          id_produto INT REFERENCES produtos(id),
          id_tabela INT REFERENCES tabelas_preco(id),
          preco_vendadecimal REAL, preco_custodecimal REAL, margemdecimal REAL,
          data_ultima_atualizacao TEXT DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(id_produto, id_tabela),
          {sync_cols}
        )
    """)

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS sequencias (
          nome VARCHAR(50) PRIMARY KEY, valor INTEGER NOT NULL, prefixo VARCHAR(10),
          {sync_cols}
        )
    """)

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS produto_codigos_alternativos (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          id_produto INT NOT NULL REFERENCES produtos(id) ON DELETE CASCADE,
          tipo VARCHAR(50) NOT NULL, codigo VARCHAR(64) NOT NULL UNIQUE,
          {sync_cols}
        )
    """)

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS fornecedores (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          nome VARCHAR(255) NOT NULL, cnpj VARCHAR(18), contato TEXT,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          {sync_cols}
        )
    """)

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS depositos (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          empresa_id INT REFERENCES empresas(id),
          nome VARCHAR(200), codigo VARCHAR(50), endereco TEXT,
          {sync_cols}
        )
    """)

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS estoque (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          id_produto INT REFERENCES produtos(id), id_deposito INT REFERENCES depositos(id),
          quantidade REAL DEFAULT 0, custo_medio REAL, updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(id_produto, id_deposito),
          {sync_cols}
        )
    """)
    
    # --- 5. FINANCEIRO (Completo) ---
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS contas_financeiras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL REFERENCES empresas(id),
            nome TEXT NOT NULL, tipo TEXT NOT NULL,
            saldo_inicial REAL DEFAULT 0.0, saldo_atual REAL DEFAULT 0.0,
            permite_transferencia_pdv BOOLEAN DEFAULT 0, active BOOLEAN DEFAULT 1,
            {sync_cols}
        )
    """)

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS categorias_financeiras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL, tipo TEXT NOT NULL, parent_id INTEGER REFERENCES categorias_financeiras(id),
            {sync_cols}
        )
    """)

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS centros_de_custo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL REFERENCES empresas(id),
            nome TEXT NOT NULL, codigo TEXT,
            {sync_cols}
        )
    """)

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS titulos_financeiros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL REFERENCES empresas(id),
            tipo TEXT NOT NULL, cliente_id INTEGER REFERENCES clientes(id),
            fornecedor_id INTEGER REFERENCES fornecedores(id),
            categoria_id INTEGER REFERENCES categorias_financeiras(id),
            centro_custo_id INTEGER REFERENCES centros_de_custo(id),
            data_emissao TEXT DEFAULT CURRENT_TIMESTAMP, data_competencia TEXT,
            numero_documento TEXT, descricao TEXT, valor_total REAL NOT NULL,
            status TEXT DEFAULT 'PENDENTE',
            {sync_cols}
        )
    """)

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS lancamentos_financeiros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo_id INTEGER NOT NULL REFERENCES titulos_financeiros(id) ON DELETE CASCADE,
            tipo TEXT NOT NULL, categoria_id INTEGER REFERENCES categorias_financeiras(id),
            centro_custo_id INTEGER REFERENCES centros_de_custo(id),
            venda_id INTEGER REFERENCES vendas(id),
            descricao TEXT, valor_previsto REAL NOT NULL, data_vencimento TEXT NOT NULL,
            status TEXT DEFAULT 'PENDENTE', data_pagamento TEXT, valor_pago REAL,
            juros REAL, multa REAL, desconto REAL,
            {sync_cols}
        )
    """)
    
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS movimentacoes_contas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conta_id INTEGER NOT NULL REFERENCES contas_financeiras(id),
            lancamento_id INTEGER REFERENCES lancamentos_financeiros(id),
            caixa_sessao_id INTEGER REFERENCES caixa_sessoes(id),
            tipo_movimento TEXT NOT NULL, valor REAL NOT NULL,
            data_movimento TEXT DEFAULT CURRENT_TIMESTAMP, descricao TEXT,
            conciliado BOOLEAN DEFAULT 0,
            {sync_cols}
        )
    """)
    
    # --- NOVO: MOTIVOS DE CANCELAMENTO ---
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS motivos_cancelamento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao TEXT NOT NULL UNIQUE,
            ativo BOOLEAN DEFAULT 1,
            {sync_cols}
        )
    """)

    
    # --- USUÁRIO ADMIN PADRÃO ---
    cursor.execute("SELECT id FROM usuarios WHERE username = 'admin'")
    admin_exists = cursor.fetchone()
    if not admin_exists:
        cursor.execute("INSERT INTO usuarios (username, password_text) VALUES ('admin', 'admin')")
        user_id = cursor.lastrowid
        
        admin_modulos = {}
        admin_formularios = {}
        admin_campos = {}
        admin_limites = {"desconto_max_perc": 100.0} 
        
        for mod_display, mod_data in PERMISSION_SCHEMA.items():
            admin_modulos[mod_data['db_key_modulo']] = True
            for form_key, form_data in mod_data['formularios'].items():
                admin_formularios[form_data['db_key_form']] = True
                admin_campos[form_key] = {}
                for field_display, field_db_key in form_data['campos'].items():
                    admin_campos[form_key][field_db_key] = "Total" 

        modulos_json = json.dumps(admin_modulos)
        formularios_json = json.dumps(admin_formularios)
        campos_json = json.dumps(admin_campos)
        limites_json = json.dumps(admin_limites)
        
        cursor.execute(
            "INSERT INTO permissoes (user_id, modulos, formularios, campos, limites) VALUES (?, ?, ?, ?, ?)",
            (user_id, modulos_json, formularios_json, campos_json, limites_json)
        )
    
    conn.commit()
    
    # --- MIGRAÇÃO AUTOMÁTICA (ADICIONA COLUNAS NOVAS EM BANCOS EXISTENTES) ---
    tabelas_existentes = [
        "usuarios", "permissoes", "clientes", "empresas", "locais_escrituracao", "terminais_pdv",
        "caixa_sessoes", "vendas", "vendas_itens", "vendas_pagamentos", "caixa_movimentacoes",
        "categorias", "produtos", "tabelas_preco", "produto_tabela_preco", "sequencias",
        "produto_codigos_alternativos", "fornecedores", "depositos", "estoque",
        "contas_financeiras", "categorias_financeiras", "centros_de_custo", "titulos_financeiros",
        "lancamentos_financeiros", "movimentacoes_contas", "motivos_cancelamento"
    ]

    def add_column_if_not_exists(table, column, definition):
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        except sqlite3.OperationalError: pass

    # 1. Adiciona colunas de negócio
    add_column_if_not_exists("produtos", "data_validade", "DATE")
    add_column_if_not_exists("produtos", "caminho_imagem", "TEXT")
    add_column_if_not_exists("terminais_pdv", "conta_financeira_id", "INTEGER REFERENCES contas_financeiras(id)")
    add_column_if_not_exists("terminais_pdv", "conta_destino_dinheiro_id", "INTEGER REFERENCES contas_financeiras(id)")
    add_column_if_not_exists("terminais_pdv", "conta_destino_cartao_id", "INTEGER REFERENCES contas_financeiras(id)")
    add_column_if_not_exists("terminais_pdv", "conta_destino_pix_id", "INTEGER REFERENCES contas_financeiras(id)")
    add_column_if_not_exists("terminais_pdv", "conta_destino_outros_id", "INTEGER REFERENCES contas_financeiras(id)")

    # 2. Adiciona colunas de Sincronização (UUID, Status) em TODAS as tabelas
    for tabela in tabelas_existentes:
        try:
            # Adiciona coluna UUID
            cursor.execute(f"ALTER TABLE {tabela} ADD COLUMN uuid TEXT UNIQUE")
            # Se conseguiu adicionar (não existia), preenche com UUIDs para dados antigos
            cursor.execute(f"SELECT id FROM {tabela}")
            rows = cursor.fetchall()
            for row in rows:
                new_uid = str(uuid.uuid4())
                cursor.execute(f"UPDATE {tabela} SET uuid = ? WHERE id = ?", (new_uid, row['id']))
        except sqlite3.OperationalError: pass 

        add_column_if_not_exists(tabela, "created_at", "TEXT DEFAULT CURRENT_TIMESTAMP")
        add_column_if_not_exists(tabela, "updated_at", "TEXT DEFAULT CURRENT_TIMESTAMP")
        add_column_if_not_exists(tabela, "sync_status", "INTEGER DEFAULT 0")
        add_column_if_not_exists(tabela, "is_deleted", "INTEGER DEFAULT 0")

        # Cria TRIGGER para atualizar updated_at e sync_status automaticamente
        trigger_name = f"trigger_update_{tabela}"
        cursor.execute(f"DROP TRIGGER IF EXISTS {trigger_name}")
        cursor.execute(f"""
            CREATE TRIGGER {trigger_name}
            AFTER UPDATE ON {tabela}
            BEGIN
                UPDATE {tabela} 
                SET updated_at = CURRENT_TIMESTAMP, 
                    sync_status = 0 
                WHERE id = NEW.id;
            END;
        """)

    try:
        cursor.execute("UPDATE empresas SET status = 1 WHERE status IS NULL")
        cursor.execute("UPDATE locais_escrituracao SET status = 1 WHERE status IS NULL")
    except Exception: pass
    
    conn.commit()
    
    # Popula dados
    populate_initial_data(cursor)
    conn.commit()
    conn.close()

# Garante que as tabelas sejam criadas na inicialização
if __name__ != "__main__":
    create_tables()