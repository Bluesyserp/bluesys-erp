# modules/pos_controller.py
import json
import sqlite3
import socket
import logging
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import Qt
from database.db import get_connection

class PosController:
    """
    Controlador de Serviços do Ponto de Venda.
    Gerencia validação de terminal, status de caixa, permissões e finalização de transações.
    """
    def __init__(self, user_id):
        
        self.user_id = user_id
        self.logger = logging.getLogger(__name__)
        
        self.terminal_data = None
        self.terminal_id = None
        self.local_id = None
        self.empresa_id = None
        self.nome_terminal = "N/A"
        self.habilita_nao_fiscal = False
        
        # --- Propriedades para o modelo CNPJ/Tabela ---
        self.identificador_loja = None
        self.tabela_id_ativa = None
        self.deposito_id_padrao = None # ID do depósito de onde baixa o estoque
        
        # --- NOVAS Propriedades Financeiras (Roteamento) ---
        self.conta_pdv_id = None    # ID da conta 'PDV / Caixa Operador'
        self.conta_dest_dinheiro_id = None
        self.conta_dest_cartao_id = None
        self.conta_dest_pix_id = None
        self.conta_dest_outros_id = None
        
        self.current_caixa_id = None
        self.user_field_permissions = {}
        self.limite_desconto = 100.0 
        
        self.is_terminal_valid = self._validate_terminal()
        if self.is_terminal_valid:
            self._load_active_price_tabela()
            self._load_user_permissions()
        
    def _validate_terminal(self):
        """Verifica se esta máquina (hostname) está cadastrada como um terminal ativo e carrega o CNPJ/Identificador."""
        try:
            hostname = socket.gethostname()
        except Exception:
            self.logger.error(f"Falha ao obter hostname.", exc_info=True)
            return False
            
        conn = get_connection()
        try:
            cur = conn.cursor()
            
            cur.execute("""
                SELECT * FROM terminais_pdv 
                WHERE hostname = ? AND status = 1
            """, (hostname,))
            data = cur.fetchone()
            
            if data is None: 
                self.logger.warning(f"Tentativa de login em terminal não cadastrado ou inativo. Hostname: {hostname}")
                return False
            
            self.terminal_data = dict(data)
            self.terminal_id = self.terminal_data['id']
            self.local_id = self.terminal_data['local_id']
            self.empresa_id = self.terminal_data['empresa_id']
            self.nome_terminal = self.terminal_data['nome_terminal']
            self.habilita_nao_fiscal = bool(self.terminal_data.get('habilita_nao_fiscal', 1))
            
            self.deposito_id_padrao = self.terminal_data.get('deposito_id_padrao', None)
            
            # Carrega IDs das contas financeiras de Roteamento
            self.conta_pdv_id = self.terminal_data.get('conta_financeira_id', None)
            self.conta_dest_dinheiro_id = self.terminal_data.get('conta_destino_dinheiro_id', None)
            self.conta_dest_cartao_id = self.terminal_data.get('conta_destino_cartao_id', None)
            self.conta_dest_pix_id = self.terminal_data.get('conta_destino_pix_id', None)
            self.conta_dest_outros_id = self.terminal_data.get('conta_destino_outros_id', None)
            
            cur.execute("SELECT cnpj FROM locais_escrituracao WHERE id = ?", (self.local_id,))
            local_cnpj_data = cur.fetchone()
            local_cnpj = local_cnpj_data['cnpj'] if local_cnpj_data else None
            
            if not local_cnpj:
                 cur.execute("SELECT cnpj FROM empresas WHERE id = ?", (self.empresa_id,))
                 empresa_cnpj_data = cur.fetchone()
                 local_cnpj = empresa_cnpj_data['cnpj'] if empresa_cnpj_data else None
                 
            self.identificador_loja = local_cnpj
            
            # Validação Financeira
            if (self.conta_pdv_id is None or 
                self.conta_dest_dinheiro_id is None or
                self.conta_dest_cartao_id is None or
                self.conta_dest_pix_id is None or
                self.conta_dest_outros_id is None):
                
                self.logger.error(f"Terminal ID {self.terminal_id} ({hostname}) não possui todos os vínculos financeiros cadastrados.")
                QMessageBox.critical(None, "Erro de Vínculo Financeiro",
                    "Este terminal não possui todas as 5 contas financeiras (PDV, Destino Dinheiro, Cartão, PIX, Outros) vinculadas.\n\n"
                    "Acesse o Cadastro de Terminais e configure os vínculos na Aba Geral.")
                return False
            
            self.logger.info(f"Terminal '{self.nome_terminal}' (ID: {self.terminal_id}) validado com sucesso.")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao validar terminal {hostname}: {e}", exc_info=True)
            return False
        finally:
            conn.close()

    def _load_active_price_tabela(self):
        """Busca a Tabela de Preço Ativa vinculada ao CNPJ do terminal."""
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT id FROM tabelas_preco 
                WHERE identificador_loja = ? AND active = 1
                LIMIT 1
            """, (self.identificador_loja,))
            
            tabela = cur.fetchone()
            self.tabela_id_ativa = tabela['id'] if tabela else None
            
        except Exception as e:
            self.logger.error(f"Erro ao carregar tabela de preço para o identificador {self.identificador_loja}: {e}", exc_info=True)
            self.tabela_id_ativa = None
        finally:
            conn.close()

    def _load_user_permissions(self):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT campos, limites FROM permissoes WHERE user_id = ?", (self.user_id,))
            perms = cur.fetchone()
            
            if perms:
                if perms['campos']:
                    all_campos = json.loads(perms['campos'])
                    self.user_field_permissions = all_campos.get('sales_form', {})
                if perms['limites']:
                    all_limites = json.loads(perms['limites'])
                    self.limite_desconto = all_limites.get('desconto_max_perc', 100.0)
            
        except Exception as e:
            self.logger.error(f"Erro ao carregar permissões do PDV para User ID {self.user_id}: {e}", exc_info=True)
            self.user_field_permissions = {}
        finally:
            conn.close()
            
    def check_caixa_status(self):
        if not self.is_terminal_valid:
            self.current_caixa_id = None
            return

        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id FROM caixa_sessoes WHERE user_id = ? AND terminal_id = ? AND status = 'ABERTO'", 
                        (self.user_id, self.terminal_id))
            caixa_aberto = cur.fetchone()
            if caixa_aberto:
                self.current_caixa_id = caixa_aberto['id']
            else:
                self.current_caixa_id = None
        except Exception as e:
            self.current_caixa_id = None 
            self.logger.error(f"Erro ao verificar status do caixa (User ID {self.user_id}, Terminal ID {self.terminal_id}): {e}", exc_info=True)
            QMessageBox.critical(None, "Erro de Caixa", f"Erro ao verificar status do caixa: {e}")
        finally:
            conn.close()

    def finalize_sale(self, cart_items, pagamentos, troco, subtotal, 
                      desconto_itens, desconto_geral, total_final, 
                      current_cliente_id, tipo_documento='FISCAL'):
        """Salva uma NOVA transação completa no DB e baixa o estoque."""
        
        if self.deposito_id_padrao is None:
            self.logger.warning(f"Tentativa de venda sem depósito padrão (User ID {self.user_id}, Terminal ID {self.terminal_id}).")
            QMessageBox.critical(None, "Erro de Terminal", "O depósito padrão não está configurado neste terminal.")
            return {"success": False, "error": "Depósito padrão não configurado."}

        current_sale_number = self.terminal_data['numero_nfe_atual'] + 1
        next_sale_number = current_sale_number
        
        conn = get_connection()
        cur = conn.cursor()
        
        sale_data_for_receipt = {}
        
        try:
            conn.execute("BEGIN")
            total_pago = sum(p['valor'] for p in pagamentos)
            
            # 1. Salva Venda
            cur.execute("""
                INSERT INTO vendas (
                    user_id, cliente_id, caixa_id, 
                    empresa_id, local_id, terminal_id, numero_venda_terminal,
                    subtotal, desconto_itens, desconto_geral, 
                    total_final, total_pago, troco, tipo_documento 
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.user_id, current_cliente_id, self.current_caixa_id,
                self.empresa_id, self.local_id, self.terminal_id, current_sale_number,
                subtotal, desconto_itens, desconto_geral,
                total_final, total_pago, troco, tipo_documento
            ))
            venda_id = cur.lastrowid
            
            dados_itens_para_cupom = []
            
            # 2. Salva Itens e Baixa Estoque
            for item in cart_items:
                total_item = (item['preco_unitario'] * item['quantidade']) - item['desconto_item']
                
                cur.execute("""
                    INSERT INTO vendas_itens (venda_id, produto_id, codigo_barras, descricao, quantidade, preco_unitario, desconto_item, total_item)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (venda_id, item['produto_id'], item['codigo_barras'], item['descricao'], item['quantidade'], 
                      item['preco_unitario'], item['desconto_item'], total_item))
                
                quantidade_baixa = -item['quantidade']
                
                cur.execute("""
                    INSERT INTO estoque (id_produto, id_deposito, quantidade, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(id_produto, id_deposito) DO UPDATE SET
                        quantidade = quantidade + excluded.quantidade,
                        updated_at = CURRENT_TIMESTAMP
                """, (item['produto_id'], self.deposito_id_padrao, quantidade_baixa)) 
                
                item_cupom = item.copy()
                item_cupom['total_item'] = total_item
                dados_itens_para_cupom.append(item_cupom)
            
            # 4. Salva Pagamentos
            for pg in pagamentos:
                forma = pg['forma']
                valor = pg['valor']
                tipo_pagamento = pg.get('tipo_pagamento', None) 
                tipo_cartao = pg.get('tipo_cartao', None)     
                parcelas = pg.get('parcelas', 1)             
                nsu = pg.get('nsu', None)
                doc = pg.get('doc', None)
                
                cur.execute("""
                    INSERT INTO vendas_pagamentos (
                        venda_id, forma, valor, tipo_pagamento, nsu, doc, 
                        tipo_cartao, parcelas
                    ) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (venda_id, forma, valor, tipo_pagamento, nsu, doc,
                      tipo_cartao, parcelas))
            
            # 5. Atualiza Sequencial do Terminal
            cur.execute(
                "UPDATE terminais_pdv SET numero_nfe_atual = ? WHERE id = ?",
                (next_sale_number, self.terminal_id)
            )
            
            conn.commit()
            
            self.terminal_data['numero_nfe_atual'] = next_sale_number
            
            self.logger.info(f"VENDA FINALIZADA (Tipo: {tipo_documento}). ID: {venda_id}, N°: {current_sale_number}, Caixa: {self.current_caixa_id}, User: {self.user_id}, Total: R$ {total_final:.2f}")
            
            sale_data_for_receipt = {
                "venda_id": venda_id,
                "user_id": self.user_id,
                "cliente_id": current_cliente_id,
                "empresa_id": self.empresa_id,
                "local_id": self.local_id,
                "terminal_id": self.terminal_id,
                "numero_venda_terminal": current_sale_number,
                "cart_items": dados_itens_para_cupom,
                "pagamentos": pagamentos,
                "subtotal": subtotal,
                "desconto_itens": desconto_itens,
                "desconto_geral": desconto_geral,
                "total_final": total_final,
                "troco": troco,
                "tipo_documento": tipo_documento
            }
            return {"success": True, "sale_number": current_sale_number, "receipt_data": sale_data_for_receipt}

        except Exception as e:
            conn.rollback()
            self.logger.error(f"FALHA ao finalizar venda (User ID {self.user_id}, Caixa ID {self.current_caixa_id}). Erro: {e}", exc_info=True)
            return {"success": False, "error": f"Erro ao salvar venda: {e}"}
        finally:
            conn.close()

    def get_receipt_data_for_venda(self, venda_id):
        conn = get_connection()
        try:
            cur = conn.cursor()
            
            cur.execute("SELECT * FROM vendas WHERE id = ?", (venda_id,))
            venda = cur.fetchone()
            if not venda:
                return {"success": False, "error": "Venda original não encontrada."}
            
            venda_dict = dict(venda)
            
            cur.execute("SELECT * FROM vendas_itens WHERE venda_id = ?", (venda_id,))
            itens = cur.fetchall()
            cart_items = [dict(item) for item in itens]
            
            cur.execute("SELECT * FROM vendas_pagamentos WHERE venda_id = ?", (venda_id,))
            pagamentos = cur.fetchall()
            pagamentos_list = [dict(pg) for pg in pagamentos]

            receipt_data = {
                "venda_id": venda_dict['id'],
                "user_id": venda_dict['user_id'],
                "cliente_id": venda_dict['cliente_id'],
                "empresa_id": venda_dict['empresa_id'],
                "local_id": venda_dict['local_id'],
                "terminal_id": venda_dict['terminal_id'],
                "numero_venda_terminal": venda_dict['numero_venda_terminal'],
                "cart_items": cart_items,
                "pagamentos": pagamentos_list,
                "subtotal": venda_dict['subtotal'],
                "desconto_itens": venda_dict['desconto_itens'],
                "desconto_geral": venda_dict['desconto_geral'],
                "total_final": venda_dict['total_final'],
                "troco": venda_dict['troco'],
                "tipo_documento": venda_dict['tipo_documento']
            }
            return {"success": True, "data": receipt_data}

        except Exception as e:
            return {"success": False, "error": f"Erro ao buscar dados do cupom: {e}"}
        finally:
            conn.close()
    
    def convert_to_fiscal(self, venda_id_para_converter):
        current_sale_number = self.terminal_data['numero_nfe_atual'] + 1
        next_sale_number = current_sale_number
        
        conn = get_connection()
        try:
            conn.execute("BEGIN")
            cur = conn.cursor()
            
            cur.execute("""
                UPDATE vendas 
                SET 
                    tipo_documento = 'FISCAL',
                    numero_venda_terminal = ? 
                WHERE id = ?
            """, (current_sale_number, venda_id_para_converter))
            
            cur.execute(
                "UPDATE terminais_pdv SET numero_nfe_atual = ? WHERE id = ?",
                (next_sale_number, self.terminal_id)
            )
            
            conn.commit()
            
            self.terminal_data['numero_nfe_atual'] = next_sale_number
            
            self.logger.info(f"CONVERSÃO P/ FISCAL (User ID {self.user_id}). Venda ID: {venda_id_para_converter}, Novo N°: {current_sale_number}.")
            
            return {"success": True, "new_sale_number": current_sale_number}

        except Exception as e:
            conn.rollback()
            self.logger.error(f"FALHA na conversão p/ Fiscal (User ID {self.user_id}, Venda ID: {venda_id_para_converter}). Erro: {e}", exc_info=True)
            return {"success": False, "error": f"Erro ao converter venda: {e}"}
        finally:
            conn.close()

    def _get_cash_closing_totals(self, caixa_id):
        """
        Busca e calcula os totais esperados (registrados) para o fechamento.
        IMPORTANTE: Ignora vendas canceladas!
        """
        conn = get_connection()
        try:
            cur = conn.cursor()
            
            cur.execute("SELECT valor_inicial FROM caixa_sessoes WHERE id = ?", (caixa_id,))
            abertura = cur.fetchone()
            suprimento_inicial = abertura['valor_inicial'] if abertura else 0.0

            cur.execute("SELECT tipo, SUM(valor) as total_mov FROM caixa_movimentacoes WHERE caixa_id = ? GROUP BY tipo", (caixa_id,))
            movimentacoes = cur.fetchall()
            suprimentos_mov = 0.0
            sangrias_mov = 0.0
            for mov in movimentacoes:
                if mov['tipo'] == 'SUPRIMENTO':
                    suprimentos_mov = mov['total_mov']
                elif mov['tipo'] == 'SANGRIA':
                    sangrias_mov = mov['total_mov']

            cur.execute("""
                SELECT vp.forma, SUM(vp.valor) as total_forma
                FROM vendas_pagamentos vp
                JOIN vendas v ON vp.venda_id = v.id
                WHERE v.caixa_id = ? 
                  AND v.status = 'FINALIZADA'
                GROUP BY vp.forma
            """, (caixa_id,))
            
            rows_vendas = cur.fetchall()
            
            formas_pagamento = {"Dinheiro": 0.0, "Pix": 0.0, "Cartão": 0.0, "Doc. Crédito": 0.0, "Outros": 0.0}
            
            for row in rows_vendas:
                forma = row['forma']
                if forma in formas_pagamento:
                    formas_pagamento[forma] += row['total_forma']
                else:
                    formas_pagamento[forma] = row['total_forma']
            
            formas_pagamento["Dinheiro"] += suprimento_inicial
            formas_pagamento["Dinheiro"] += suprimentos_mov
            formas_pagamento["Dinheiro"] -= sangrias_mov
            
            return {"success": True, "totals": formas_pagamento}
        
        except Exception as e:
            return {"success": False, "error": f"Erro ao calcular totais do caixa: {e}"}
        finally:
            conn.close()

    def finalize_cash_closing(self, data, autorizador_id):
        totals_result = self._get_cash_closing_totals(self.current_caixa_id)
        if not totals_result["success"]:
            return totals_result
        
        expected_totals_map = totals_result["totals"]
        
        conn = get_connection()
        try:
            cur = conn.cursor()
            
            cur.execute("SELECT id FROM categorias_financeiras WHERE nome = 'Receita de Vendas PDV' AND tipo = 'RECEITA'")
            cat_venda = cur.fetchone()
            
            if not cat_venda:
                cur.execute("SELECT id FROM categorias_financeiras WHERE tipo = 'RECEITA' LIMIT 1")
                cat_venda = cur.fetchone()
            
            categoria_venda_id = cat_venda['id'] if cat_venda else None
            
            conn.execute("BEGIN")
            
            cur.execute("""
                UPDATE caixa_sessoes 
                SET 
                    status = 'FECHADO', 
                    data_fechamento = CURRENT_TIMESTAMP,
                    valor_final_calculado = ?,
                    valor_final_informado = ?,
                    diferenca = ?,
                    autorizador_id = ?
                WHERE id = ?
            """, (
                data["calculado"],
                data["informado"],
                data["diferenca"],
                autorizador_id,
                self.current_caixa_id
            ))
            
            descricao_titulo = f"Fechamento Caixa #{self.current_caixa_id} - Terminal: {self.nome_terminal}"
            valor_total_fechamento = data["calculado"] 
            
            cur.execute("""
                INSERT INTO titulos_financeiros 
                (empresa_id, tipo, categoria_id, data_emissao, descricao, valor_total, status)
                VALUES (?, 'RECEBER', ?, CURRENT_TIMESTAMP, ?, ?, 'PAGO')
            """, (self.empresa_id, categoria_venda_id, descricao_titulo, valor_total_fechamento))
            
            titulo_id = cur.lastrowid
            
            for forma_pagamento, valor in expected_totals_map.items():
                if valor == 0:
                    continue 

                destino_conta_id = None
                if forma_pagamento == "Dinheiro":
                    destino_conta_id = self.conta_dest_dinheiro_id
                elif forma_pagamento == "Cartão":
                    destino_conta_id = self.conta_dest_cartao_id
                elif forma_pagamento == "Pix":
                    destino_conta_id = self.conta_dest_pix_id
                else: 
                    destino_conta_id = self.conta_dest_outros_id

                desc_lancamento = f"Recebimento {forma_pagamento} - Fechamento Caixa #{self.current_caixa_id}"
                
                cur.execute("""
                    INSERT INTO lancamentos_financeiros
                    (titulo_id, tipo, categoria_id, descricao, valor_previsto, data_vencimento, status, data_pagamento, valor_pago)
                    VALUES (?, 'RECEBER', ?, ?, ?, DATE('now'), 'PAGO', DATE('now'), ?)
                """, (titulo_id, categoria_venda_id, desc_lancamento, valor, valor))
                
                lancamento_id = cur.lastrowid
                
                cur.execute("""
                    INSERT INTO movimentacoes_contas
                    (conta_id, lancamento_id, caixa_sessao_id, tipo_movimento, valor, descricao, conciliado)
                    VALUES (?, ?, ?, 'SAIDA', ?, ?, 1)
                """, (self.conta_pdv_id, lancamento_id, self.current_caixa_id, valor, desc_lancamento))

                cur.execute("""
                    INSERT INTO movimentacoes_contas
                    (conta_id, lancamento_id, caixa_sessao_id, tipo_movimento, valor, descricao, conciliado)
                    VALUES (?, ?, ?, 'ENTRADA', ?, ?, 1)
                """, (destino_conta_id, lancamento_id, self.current_caixa_id, valor, desc_lancamento))

                cur.execute("UPDATE contas_financeiras SET saldo_atual = saldo_atual - ? WHERE id = ?", (valor, self.conta_pdv_id))
                cur.execute("UPDATE contas_financeiras SET saldo_atual = saldo_atual + ? WHERE id = ?", (valor, destino_conta_id))

            conn.commit()
            
            self.logger.info(f"FECHAMENTO DE CAIXA (User ID {self.user_id}, Caixa ID {self.current_caixa_id}). Valor: R$ {valor_total_fechamento:.2f}.")
            
            return {"success": True}
        
        except Exception as e:
            conn.rollback()
            self.logger.error(f"FALHA no fechamento de caixa (User ID {self.user_id}, Caixa ID {self.current_caixa_id}). Erro: {e}", exc_info=True)
            return {"success": False, "error": f"Erro ao salvar fechamento financeiro: {e}"}
        finally:
            conn.close()

    def add_cash_movement(self, tipo, valor, motivo, autorizador_id=None):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO caixa_movimentacoes 
                (caixa_id, user_id, terminal_id, tipo, valor, motivo, autorizador_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                self.current_caixa_id,
                self.user_id,
                self.terminal_id,
                tipo,
                valor,
                motivo,
                autorizador_id if autorizador_id else self.user_id
            ))
            conn.commit()
            
            self.logger.info(f"MOV. CAIXA (User ID {self.user_id}, Caixa ID {self.current_caixa_id}). Tipo: {tipo}, Valor: R$ {valor:.2f}.")
            
            return {"success": True}
        except Exception as e:
            conn.rollback()
            self.logger.error(f"FALHA na mov. caixa (User ID {self.user_id}, Caixa ID {self.current_caixa_id}). Erro: {e}", exc_info=True)
            return {"success": False, "error": f"Erro ao salvar movimentação: {e}"}
        finally:
            conn.close()

    # --- NOVO MÉTODO: Cancelar Venda (Que estava faltando) ---
    def cancel_sale(self, venda_id, motivo):
        """
        Cancela uma venda do caixa ATUAL.
        1. Marca venda como CANCELADA.
        2. Devolve produtos ao estoque.
        3. Registra log e auditoria.
        """
        if not self.current_caixa_id:
             return {"success": False, "error": "Caixa não está aberto."}

        conn = get_connection()
        try:
            conn.execute("BEGIN")
            cur = conn.cursor()
            
            cur.execute("SELECT * FROM vendas WHERE id = ? AND caixa_id = ?", (venda_id, self.current_caixa_id))
            venda = cur.fetchone()
            
            if not venda:
                return {"success": False, "error": "Venda não encontrada neste caixa ou já fechada."}
            
            if venda['status'] == 'CANCELADA':
                 return {"success": False, "error": "Venda já está cancelada."}

            cur.execute("UPDATE vendas SET status = 'CANCELADA' WHERE id = ?", (venda_id,))
            
            cur.execute("SELECT produto_id, quantidade FROM vendas_itens WHERE venda_id = ?", (venda_id,))
            itens = cur.fetchall()
            
            for item in itens:
                cur.execute("""
                    UPDATE estoque 
                    SET quantidade = quantidade + ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id_produto = ? AND id_deposito = ?
                """, (item['quantidade'], item['produto_id'], self.deposito_id_padrao))
                
            conn.commit()
            
            self.logger.info(f"VENDA CANCELADA (User ID {self.user_id}). Venda ID: {venda_id}. Motivo: {motivo}")
            
            return {"success": True}
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"FALHA ao cancelar venda {venda_id}: {e}", exc_info=True)
            return {"success": False, "error": f"Erro ao cancelar venda: {e}"}
        finally:
            conn.close()