# config/permissions.py

FIELD_PERMISSIONS = ["Total", "Leitura", "Oculto"]
MODULE_PERMISSIONS = ["Negado", "Permitido"]

PERMISSION_SCHEMA = {
    "Cadastros": {
        "db_key_modulo": "mod_cadastros", 
        "formularios": {
            "form_product": {
                "display_name": "Cadastro de Produtos (Formulário)",
                "db_key_form": "form_product", 
                "campos": {
                    "Aba: Estoque": "tab_estoque",
                    "Aba: Composição": "tab_composicao",
                    "Aba: Fornecedores": "tab_fornecedores",
                    "Campo: Preço de Compra": "preco_compra",
                    "Campo: Preço de Custo": "preco_custo",
                    "Campo: Margem %": "margem",
                    "Grupo: Fiscal (NCM, CST, Alíquotas)": "group_fiscal",
                }
            },
            "form_product_list": {
                "display_name": "Materiais e Produtos (Consulta)",
                "db_key_form": "form_product_list",
                "campos": {
                    "Botão: Editar": "btn_edit",
                }
            },
            "form_customer": {
                "display_name": "Cadastro de Clientes",
                "db_key_form": "form_customer",
                "campos": {
                    "Botão: Salvar": "btn_salvar",
                    "Botão: Excluir": "btn_excluir",
                }
            },
            "form_category": {
                "display_name": "Cadastro de Classes (Categorias)",
                "db_key_form": "form_category",
                "campos": {
                    "Botão: Salvar": "btn_salvar",
                    "Botão: Excluir": "btn_excluir",
                }
            },
            "form_fornecedor": {
                "display_name": "Cadastro de Fornecedores",
                "db_key_form": "form_fornecedor",
                "campos": {
                    "Botão: Salvar": "btn_salvar",
                    "Botão: Excluir": "btn_excluir",
                    "Acesso: Importar CSV": "btn_import_csv",
                    "Acesso: Exportar CSV": "btn_export_csv"
                }
            }
        }
    },
    "Config. Empresa": {
        "db_key_modulo": "mod_empresa_config",
        "formularios": {
            "form_empresas": { 
                "display_name": "Cadastro de Empresas",
                "db_key_form": "form_empresas",
                "campos": {}
            },
            "form_locais_escrituracao": { 
                "display_name": "Cadastro de Locais de Escrituração",
                "db_key_form": "form_locais_escrituracao",
                "campos": {}
            },
            "form_depositos": {
                "display_name": "Locais de Estoque (Depósitos)",
                "db_key_form": "form_depositos",
                "campos": {}
            },
            "form_pricing_manager": {
                "display_name": "Gestão de Preços (CNPJ)",
                "db_key_form": "form_pricing_manager",
                "campos": {
                    "Aba: Vínculo CNPJ / Tabela": "tab_vinculo_cnpj",
                    "Aba: Precificação / Importação": "tab_precificacao",
                    "Acesso: Importar CSV Preços": "btn_import_csv",
                    "Acesso: Exportar CSV Preços": "btn_export_csv"
                }
            }
        }
    },
    "Comercial": {
        "db_key_modulo": "mod_comercial", 
        "formularios": {
            "sales_form": {
                "display_name": "Ponto de Venda (PDV)",
                "db_key_form": "form_sales",
                "campos": {
                    "Acesso: Abrir Caixa": "pode_abrir_caixa",
                    "Acesso: Fechar Caixa": "pode_fechar_caixa",
                    "Acesso: Fechar Caixa com Divergência": "pode_fechar_com_divergencia",
                    "Acesso: Fazer Sangria (Saída)": "pode_fazer_sangria",
                    "Acesso: Fazer Suprimento (Entrada)": "pode_fazer_suprimento",
                    "Acesso: Excluir Item da Venda": "pode_excluir_item",
                    "Acesso: Dar Desconto no Item": "pode_desconto_item",
                    "Acesso: Dar Desconto na Venda": "pode_desconto_venda",
                    "Botão: Buscar Produto (F7)": "btn_buscar_produto",
                    
                    "Botão: Finalizar Venda (Fiscal)": "pode_finalizar_fiscal",
                    "Botão: Finalizar Venda (Não-Fiscal)": "pode_finalizar_nao_fiscal",
                    "Botão: Cancelar Venda": "btn_cancelar",
                    
                    "Acesso: Carregar Pré-Venda/Não-Fiscal": "pode_carregar_prevenda",
                    "Acesso: Converter Não-Fiscal em Fiscal": "pode_converter_fiscal"
                }
            },
            "form_terminais_pdv": { 
                "display_name": "Config. Terminais (PDV)",
                "db_key_form": "form_terminais_pdv",
                "campos": {}
            },
            "form_impressoras": { 
                "display_name": "Config. Impressoras",
                "db_key_form": "form_impressoras",
                "campos": {}
            },
            # --- NOVO: Motivos de Cancelamento ---
            "form_motivos_cancelamento": { 
                "display_name": "Motivos de Cancelamento",
                "db_key_form": "form_motivos_cancelamento",
                "campos": {}
            },
            # --- FIM NOVO ---
            "relatorio_vendas_caixa": { 
                "display_name": "Relatório de Vendas por Caixa",
                "db_key_form": "relatorio_vendas_caixa",
                "campos": {}
            },
            "relatorio_vendas_produto": { 
                "display_name": "Relatório de Vendas por Produto",
                "db_key_form": "relatorio_vendas_produto",
                "campos": {}
            },
            "consulta_prevendas": {
                "display_name": "Consulta de Pré-Vendas",
                "db_key_form": "consulta_prevendas",
                "campos": {}
            }
        }
    },
    "Administração": {
        "db_key_modulo": "mod_administracao",
        "formularios": {
            "admin_form": {
                "display_name": "Formulário de Admin",
                "db_key_form": "form_admin",
                "campos": {
                    "Botão: Excluir Usuário": "delete_btn",
                    "Campo: Limite de Desconto %": "campo_limite_desconto" 
                }
            }
        }
    },
    "Contábil": {"db_key_modulo": "mod_contabil", "formularios": {}},
    "DP": {"db_key_modulo": "mod_dp", "formularios": {}},
    
    "Financeiro": {
        "db_key_modulo": "mod_financeiro", 
        "formularios": {
            "form_financeiro": {
                "display_name": "Dashboard Financeiro",
                "db_key_form": "form_financeiro",
                "campos": {
                    "Aba: Lançamentos": "tab_lancamentos",
                    "Aba: Extrato de Contas": "tab_extrato",
                    "Botão: Novo Lançamento": "btn_novo_lancamento",
                    "Botão: Baixar Lançamento": "btn_baixar",
                    "Botão: Estornar Baixa": "btn_estornar",
                    "Botão: Excluir Lançamento": "btn_excluir_lanc",
                }
            },
            "form_contas_financeiras": {
                "display_name": "Cadastro de Contas (Disponíveis)",
                "db_key_form": "form_contas_financeiras",
                "campos": {}
            },
            "form_categorias_financeiras": {
                "display_name": "Plano de Contas (Categorias)",
                "db_key_form": "form_categorias_financeiras",
                "campos": {}
            },
            "form_centros_de_custo": {
                "display_name": "Cadastro de Centros de Custo",
                "db_key_form": "form_centros_de_custo",
                "campos": {}
            },
            "form_relatorio_dre": {
                "display_name": "Relatório DRE (Demonstrativo)",
                "db_key_form": "form_relatorio_dre",
                "campos": {}
            },
            "form_relatorio_fluxo_caixa": {
                "display_name": "Relatório Fluxo de Caixa (Extrato)",
                "db_key_form": "form_relatorio_fluxo_caixa",
                "campos": {}
            }
        }
    },
    
    "Fiscal": {"db_key_modulo": "mod_fiscal", "formularios": {}},
    "Logística": {"db_key_modulo": "mod_logistica", "formularios": {}},
    "Operação": {"db_key_modulo": "mod_operacao", "formularios": {}},
    "Relatórios": {"db_key_modulo": "mod_relatorios", "formularios": {}},
}