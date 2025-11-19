# modules/printing_service.py
import os
import tempfile
import sqlite3
import win32print
import win32api
import shutil
import io
import qrcode
import re 
from datetime import datetime
from PyQt5.QtWidgets import QMessageBox, QFileDialog

from database.db import get_connection

# --- Importações do ReportLab ---
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import mm
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.lib.utils import ImageReader
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# --- Constantes do Cupom ---
WIDTH = 80 * mm 
MARGIN_LEFT = 3 * mm
MARGIN_RIGHT = WIDTH - (3 * mm)

# -------------------------------------------------------------------
# --- FUNÇÕES DE IMPRESSÃO (COMPARTILHADAS) ---
# -------------------------------------------------------------------

def _save_virtual_pdf(pdf_path, suggested_name):
    """
    Abre um QFileDialog para salvar o PDF virtualmente.
    """
    try:
        save_path, _ = QFileDialog.getSaveFileName(
            None, 
            "Salvar PDF", 
            suggested_name, 
            "PDF Files (*.pdf)"
        )
        
        if save_path:
            shutil.copy(pdf_path, save_path)
            try:
                win32api.ShellExecute(0, "open", f'"{save_path}"', None, ".", 1)
            except Exception as e_open:
                print(f"Não foi possível abrir o PDF salvo: {e_open}")

    except Exception as e:
        QMessageBox.warning(None, "Erro ao Salvar PDF", 
            f"Não foi possível salvar o cupom virtual.\n\nErro: {e}")
    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)

def _print_physical(pdf_path, printer_name):
    """
    Envia o PDF diretamente para uma impressora física ou para a
    'Microsoft Print to PDF' (usando o verbo 'printto').
    """
    if not printer_name:
        try:
            printer_name = win32print.GetDefaultPrinter()
        except Exception:
            QMessageBox.warning(None, "Erro ao Imprimir", 
                "Nenhuma impressora configurada no terminal e falha ao obter a impressora padrão do Windows.")
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
            return

    try:
        win32api.ShellExecute(
            0,
            "printto", 
            f'"{pdf_path}"',
            f'"{printer_name}"',
            ".",
            0
        )
    except Exception as e:
        QMessageBox.warning(None, "Erro ao Imprimir", 
            f"Não foi possível imprimir o cupom na impressora '{printer_name}'.\n"
            f"Verifique se a impressora está online.\n\n"
            f"Erro Técnico: {e}")
    finally:
        if os.path.exists(pdf_path):
            try:
                import time
                time.sleep(2) 
                os.remove(pdf_path)
            except:
                pass

def _get_printer_name(conn, terminal_id):
    """Busca o nome da impressora no terminal e o sanitiza."""
    cur = conn.cursor()
    cur.execute("SELECT impressora_nome FROM terminais_pdv WHERE id = ?", (terminal_id,))
    terminal = cur.fetchone()
    
    if terminal and terminal['impressora_nome']:
        raw_name = terminal['impressora_nome']
        clean_name = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', raw_name).strip()
        return clean_name
        
    return None

# -------------------------------------------------------------------
# --- CLASSE PRINCIPAL ---
# -------------------------------------------------------------------

class ReceiptPrinter:
    def __init__(self, sale_data):
        self.sale_data = sale_data
        self.full_data = {}
        self.pdf_path = ""
        self.c = None
        
        # --- CÁLCULO DINÂMICO DA ALTURA (Para Vendas Normais) ---
        num_items = len(sale_data.get('cart_items', []))
        base_height = 170 * mm 
        items_height = num_items * (12 * mm) 
        
        self.page_height = base_height + items_height
        self.y_pos = self.page_height - (5 * mm) 
        
    def _load_full_data(self, conn):
        """Busca dados da empresa, local, cliente e operador."""
        cur = conn.cursor()
        
        cur.execute("""
            SELECT e.razao_social, e.nome_fantasia, e.cnpj, e.inscricao_estadual AS ie,
                   l.nome_local, l.end_logradouro, l.end_numero, l.end_bairro, l.end_municipio, l.end_uf
            FROM empresas e
            JOIN locais_escrituracao l ON e.id = l.empresa_id
            WHERE e.id = ? AND l.id = ?
        """, (self.sale_data['empresa_id'], self.sale_data['local_id']))
        empresa_local = cur.fetchone()
        
        cur.execute("SELECT serie_fiscal, ambiente FROM terminais_pdv WHERE id = ?", (self.sale_data['terminal_id'],))
        terminal = cur.fetchone()

        cur.execute("SELECT nome_razao, cpf, cnpj FROM clientes WHERE id = ?", (self.sale_data['cliente_id'],))
        cliente = cur.fetchone()

        cur.execute("SELECT username FROM usuarios WHERE id = ?", (self.sale_data['user_id'],))
        operador = cur.fetchone()
        
        self.full_data = {
            "empresa": dict(empresa_local) if empresa_local else {},
            "terminal": dict(terminal) if terminal else {},
            "cliente": dict(cliente) if cliente else {},
            "operador": dict(operador) if operador else {},
            "venda": self.sale_data
        }
        
    def _draw_line(self, text, font, size, align=TA_LEFT, bold=False):
        if bold:
            self.c.setFont(f"{font}-Bold", size)
        else:
            self.c.setFont(font, size)
            
        if align == TA_LEFT:
            self.c.drawString(MARGIN_LEFT, self.y_pos, text)
        elif align == TA_CENTER:
            self.c.drawCentredString(WIDTH / 2, self.y_pos, text)
        elif align == TA_RIGHT:
            self.c.drawRightString(MARGIN_RIGHT, self.y_pos, text)
            
        self.y_pos -= (size * 1.2)

    def _draw_divider(self):
        self._draw_line("-" * 50, "Courier", 8, TA_CENTER)
        self.y_pos -= (1 * mm)

    def _create_temp_pdf(self, custom_height=None):
        """Cria o canvas e o caminho temporário do PDF."""
        fd, self.pdf_path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        # Se uma altura específica for passada (cancelamento), usa ela.
        height_to_use = custom_height if custom_height else self.page_height
        self.c = canvas.Canvas(self.pdf_path, pagesize=(WIDTH, height_to_use))
        self.y_pos = height_to_use - (5 * mm) # Reinicia posição Y

    def _save_and_close_pdf(self):
        """Salva o PDF e retorna o caminho."""
        self.c.showPage()
        self.c.save()
        return self.pdf_path

    # --- Cupom Simples / Não-Fiscal ---
    def _generate_non_fiscal_receipt(self):
        self._create_temp_pdf()
        emp = self.full_data["empresa"]
        venda = self.full_data["venda"]
        
        self._draw_line(emp.get('nome_fantasia', emp.get('razao_social', 'NOME DA EMPRESA')), "Helvetica", 10, TA_CENTER, bold=True)
        self._draw_line(f"CNPJ: {emp.get('cnpj', 'N/A')}", "Helvetica", 8, TA_CENTER)
        self._draw_divider()

        self._draw_line("CUPOM NÃO-FISCAL", "Helvetica", 11, TA_CENTER, bold=True)
        self._draw_line(f"Venda Nº: {venda['numero_venda_terminal']}", "Helvetica", 11, TA_CENTER, bold=True)
        self._draw_line(datetime.now().strftime("%d/%m/%Y %H:%M:%S"), "Helvetica", 8, TA_CENTER)
        self._draw_divider()

        self.c.setFont("Courier", 8)
        self.c.drawString(MARGIN_LEFT, self.y_pos, "# Descrição")
        self.c.drawRightString(MARGIN_RIGHT, self.y_pos, "Qtd X Vl.Unit = Vl.Total")
        self.y_pos -= (8 * 1.2)

        for i, item in enumerate(self.full_data["venda"]["cart_items"]):
            self.c.setFont("Courier", 8)
            desc = f"{i+1:03} {item['descricao']}"
            self.c.drawString(MARGIN_LEFT, self.y_pos, desc[:40])
            self.y_pos -= (8 * 1.2)
            
            self.c.setFont("Courier-Bold", 9)
            unidade = item.get('unidade', 'UN')
            qtd_str = f"{item['quantidade']:.2f} {unidade} X {item['preco_unitario']:.2f}"
            total_str = f"{item['total_item']:.2f}"
            self.c.drawString(MARGIN_LEFT + (5*mm), self.y_pos, qtd_str)
            self.c.drawRightString(MARGIN_RIGHT, self.y_pos, total_str)
            self.y_pos -= (9 * 1.2)
            
            if item['desconto_item'] > 0:
                self.c.setFont("Courier", 8)
                self.c.drawRightString(MARGIN_RIGHT, self.y_pos, f"Desconto item: -{item['desconto_item']:.2f}")
                self.y_pos -= (8 * 1.2)
        
        self.y_pos -= (2 * mm)
        self._draw_divider()

        venda = self.full_data["venda"]
        self._draw_line(f"QTD. TOTAL DE ITENS", "Helvetica", 8, TA_LEFT)
        self.c.drawRightString(MARGIN_RIGHT, self.y_pos + (8 * 1.2), f"{len(venda['cart_items']):02}")

        self._draw_line(f"VALOR TOTAL R$", "Helvetica", 8, TA_LEFT)
        self.c.drawRightString(MARGIN_RIGHT, self.y_pos + (8 * 1.2), f"{venda['subtotal']:.2f}")

        total_descontos = venda['desconto_itens'] + venda['desconto_geral']
        if total_descontos > 0:
            self._draw_line(f"Descontos R$", "Helvetica", 8, TA_LEFT)
            self.c.drawRightString(MARGIN_RIGHT, self.y_pos + (8 * 1.2), f"-{total_descontos:.2f}")

        self._draw_line(f"VALOR A PAGAR R$", "Helvetica", 10, TA_LEFT, bold=True)
        self.c.setFont("Helvetica-Bold", 12)
        self.c.drawRightString(MARGIN_RIGHT, self.y_pos + (10 * 1.2), f"{venda['total_final']:.2f}")
        self.y_pos -= (2 * mm)

        self._draw_line("FORMA DE PAGAMENTO", "Helvetica", 8, TA_LEFT)
        self.c.drawRightString(MARGIN_RIGHT, self.y_pos + (8 * 1.2), "Valor Pago")
        
        for pg in venda["pagamentos"]:
            forma_texto = pg['forma']
            if forma_texto == "Cartão":
                tipo_cartao = pg.get('tipo_cartao', '')
                if tipo_cartao:
                    forma_texto = f"Cartão {tipo_cartao.lower()}"
            
            self._draw_line(forma_texto, "Helvetica", 9, TA_LEFT)
            self.c.drawRightString(MARGIN_RIGHT, self.y_pos + (9 * 1.2), f"{pg['valor']:.2f}")

        if venda['troco'] > 0:
            self._draw_line(f"Troco R$", "Helvetica", 9, TA_LEFT)
            self.c.drawRightString(MARGIN_RIGHT, self.y_pos + (9 * 1.2), f"{venda['troco']:.2f}")
        
        self._draw_divider()

        cli = self.full_data["cliente"]
        self._draw_line(f"Cliente: {cli.get('nome_razao', 'CONSUMIDOR FINAL')}", "Helvetica", 8, TA_CENTER)
        
        op = self.full_data["operador"].get('username', 'N/A')
        self._draw_line(f"Operador: {op}", "Helvetica", 8, TA_CENTER)
        self._draw_line("BlueSys ERP - Cupom Não-Fiscal", "Helvetica", 8, TA_CENTER)

        return self._save_and_close_pdf()
    
    # --- Cupom Fiscal ---
    def _generate_fiscal_receipt(self):
        """Cria o PDF para um cupom FISCAL (NFC-e)."""
        self._create_temp_pdf()
        emp = self.full_data["empresa"]
        venda = self.full_data["venda"]
        
        self._draw_line(emp.get('razao_social', 'NOME DA EMPRESA'), "Helvetica", 10, TA_CENTER, bold=True)
        self._draw_line(f"CNPJ: {emp.get('cnpj', 'N/A')} IE: {emp.get('ie', 'N/A')}", "Helvetica", 8, TA_CENTER)
        addr = f"{emp.get('end_logradouro', 'RUA')}, {emp.get('end_numero', 'S/N')}, {emp.get('end_bairro', 'BAIRRO')}"
        city = f"{emp.get('end_municipio', 'CIDADE')}, {emp.get('end_uf', 'UF')}"
        self._draw_line(addr, "Helvetica", 8, TA_CENTER)
        self._draw_line(city, "Helvetica", 8, TA_CENTER)
        self._draw_divider()

        self._draw_line("DOCUMENTO AUXILIAR DA NOTA FISCAL", "Helvetica", 9, TA_CENTER, bold=True)
        self._draw_line("DE CONSUMIDOR ELETRÔNICA", "Helvetica", 9, TA_CENTER, bold=True)
        
        ambiente = self.full_data["terminal"].get('ambiente', 2)
        if ambiente == 2: 
            self._draw_line("EMITIDA EM AMBIENTE DE HOMOLOGAÇÃO", "Helvetica", 9, TA_CENTER)
            self._draw_line("SEM VALOR FISCAL", "Helvetica", 9, TA_CENTER, bold=True)
        self._draw_divider()

        self.c.setFont("Courier", 8)
        self.c.drawString(MARGIN_LEFT, self.y_pos, "# Cód Descrição")
        self.c.drawRightString(MARGIN_RIGHT, self.y_pos, "Qtd Un Vl.Unit Vl.Total")
        self.y_pos -= (8 * 1.2)

        for i, item in enumerate(self.full_data["venda"]["cart_items"]):
            self.c.setFont("Courier", 8)
            desc = f"{i+1:03} {item['codigo_barras']} {item['descricao']}"
            self.c.drawString(MARGIN_LEFT, self.y_pos, desc[:40])
            self.y_pos -= (8 * 1.2)
            
            self.c.setFont("Courier-Bold", 9)
            unidade = item.get('unidade', 'UN')
            qtd_str = f"{item['quantidade']:.2f} {unidade} X {item['preco_unitario']:.2f}"
            total_str = f"{item['total_item']:.2f}"
            self.c.drawString(MARGIN_LEFT + (5*mm), self.y_pos, qtd_str)
            self.c.drawRightString(MARGIN_RIGHT, self.y_pos, total_str)
            self.y_pos -= (9 * 1.2)

            if item['desconto_item'] > 0:
                self.c.setFont("Courier", 8)
                self.c.drawRightString(MARGIN_RIGHT, self.y_pos, f"Desconto item: -{item['desconto_item']:.2f}")
                self.y_pos -= (8 * 1.2)
        
        self.y_pos -= (2 * mm)
        self._draw_divider()

        venda = self.full_data["venda"]
        self._draw_line(f"QTD. TOTAL DE ITENS", "Helvetica", 8, TA_LEFT)
        self.c.drawRightString(MARGIN_RIGHT, self.y_pos + (8 * 1.2), f"{len(venda['cart_items']):02}")

        self._draw_line(f"VALOR TOTAL R$", "Helvetica", 8, TA_LEFT)
        self.c.drawRightString(MARGIN_RIGHT, self.y_pos + (8 * 1.2), f"{venda['subtotal']:.2f}")

        total_descontos = venda['desconto_itens'] + venda['desconto_geral']
        if total_descontos > 0:
            self._draw_line(f"Descontos R$", "Helvetica", 8, TA_LEFT)
            self.c.drawRightString(MARGIN_RIGHT, self.y_pos + (8 * 1.2), f"-{total_descontos:.2f}")

        self._draw_line(f"VALOR A PAGAR R$", "Helvetica", 10, TA_LEFT, bold=True)
        self.c.setFont("Helvetica-Bold", 12)
        self.c.drawRightString(MARGIN_RIGHT, self.y_pos + (10 * 1.2), f"{venda['total_final']:.2f}")
        self.y_pos -= (2 * mm)

        self._draw_line("FORMA DE PAGAMENTO", "Helvetica", 8, TA_LEFT)
        self.c.drawRightString(MARGIN_RIGHT, self.y_pos + (8 * 1.2), "Valor Pago")
        
        for pg in venda["pagamentos"]:
            forma_texto = pg['forma']
            if forma_texto == "Cartão":
                tipo_cartao = pg.get('tipo_cartao', '')
                if tipo_cartao:
                    forma_texto = f"Cartão {tipo_cartao.lower()}"
            
            self._draw_line(forma_texto, "Helvetica", 9, TA_LEFT)
            self.c.drawRightString(MARGIN_RIGHT, self.y_pos + (9 * 1.2), f"{pg['valor']:.2f}")

        if venda['troco'] > 0:
            self._draw_line(f"Troco R$", "Helvetica", 9, TA_LEFT)
            self.c.drawRightString(MARGIN_RIGHT, self.y_pos + (9 * 1.2), f"{venda['troco']:.2f}")
        
        self._draw_divider()

        cli = self.full_data["cliente"]
        doc = cli.get('cpf', '') or cli.get('cnpj', '')
        if doc:
            self._draw_line(f"CONSUMIDOR CPF/CNPJ: {doc}", "Helvetica", 8, TA_CENTER)
        else:
            self._draw_line("CONSUMIDOR NÃO IDENTIFICADO", "Helvetica", 8, TA_CENTER)

        url_consulta = "nfce.sefaz.pe.gov.br/nfce/consulta"
        chave_acesso = "2625 1138 5024 9000 0105 6505 3000 0001 7510 0280 2624"
        
        try:
            qr_data = f"http://{url_consulta}?p={chave_acesso.replace(' ', '')}|2|...etc"
            qr = qrcode.QRCode(version=1, box_size=2, border=1)
            qr.add_data(qr_data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            
            fd_qr, qr_path = tempfile.mkstemp(suffix=".png")
            os.close(fd_qr)
            img.save(qr_path)

            qr_size = 30 * mm 
            qr_x = (WIDTH - qr_size) / 2 
            self.y_pos -= qr_size 
            self.c.drawImage(ImageReader(qr_path), qr_x, self.y_pos, width=qr_size, height=qr_size)
            
            if os.path.exists(qr_path):
                os.remove(qr_path)
            
        except Exception as e_qr:
            self._draw_line(f"[Erro ao gerar QR Code: {e_qr}]", "Helvetica", 7, TA_CENTER)

        self.y_pos -= (2 * mm)
        self._draw_line("Consulte pela Chave de Acesso em", "Helvetica", 8, TA_CENTER)
        self._draw_line(url_consulta, "Helvetica", 8, TA_CENTER, bold=True)
        self._draw_line("(Chave de Acesso simulada)", "Helvetica", 7, TA_CENTER)
        self._draw_line(chave_acesso, "Courier", 8, TA_CENTER)
        self.y_pos -= (2 * mm)
        
        term = self.full_data["terminal"]
        n_venda = venda['numero_venda_terminal']
        self._draw_line(f"NFC-e n° {n_venda} Série {term.get('serie_fiscal', 1)}", "Helvetica", 9, TA_LEFT)
        self._draw_line(datetime.now().strftime("%d/%m/%Y %H:%M:%S"), "Helvetica", 9, TA_RIGHT)
        self.y_pos -= (2 * mm)
        self._draw_line("(Protocolo de Autorização simulado)", "Helvetica", 7, TA_LEFT)
        self._draw_line("999999999999999", "Helvetica", 9, TA_LEFT)

        self._draw_divider()
        
        op = self.full_data["operador"].get('username', 'N/A')
        self._draw_line(f"Operador: {op}", "Helvetica", 8, TA_CENTER)
        self._draw_line("BlueSys ERP - www.bluesys.com.br", "Helvetica", 8, TA_CENTER)

        return self._save_and_close_pdf()
        
    # --- COMPROVANTE DE CANCELAMENTO (Novo) ---
    def _generate_cancellation_receipt(self, motivo="Não informado"):
        """Gera o PDF para o Comprovante de Cancelamento."""
        
        # Define uma altura específica e compacta (ex: 130mm)
        # para que o corte aconteça logo após o rodapé.
        cancellation_height = 130 * mm
        
        # Cria o PDF com a altura específica
        self._create_temp_pdf(custom_height=cancellation_height)
        
        emp = self.full_data["empresa"]
        venda = self.full_data["venda"]
        
        # Cabeçalho
        self._draw_line(emp.get('nome_fantasia', emp.get('razao_social', 'NOME DA EMPRESA')), "Helvetica", 10, TA_CENTER, bold=True)
        self._draw_line(f"CNPJ: {emp.get('cnpj', 'N/A')}", "Helvetica", 8, TA_CENTER)
        self._draw_divider()
        
        # Título
        self._draw_line("*** COMPROVANTE DE CANCELAMENTO ***", "Helvetica", 11, TA_CENTER, bold=True)
        self.y_pos -= (2 * mm)
        
        # Dados da Venda Cancelada
        self._draw_line(f"VENDA Nº: {venda['numero_venda_terminal']}", "Helvetica", 10, TA_LEFT, bold=True)
        self._draw_line(f"DATA VENDA: {venda['data_venda']}", "Helvetica", 9, TA_LEFT)
        self._draw_line(f"VALOR TOTAL: R$ {venda['total_final']:.2f}", "Helvetica", 10, TA_LEFT, bold=True)
        
        self._draw_divider()
        
        # Motivo
        self._draw_line("MOTIVO DO CANCELAMENTO:", "Helvetica", 9, TA_LEFT, bold=True)
        self._draw_line(motivo, "Courier", 9, TA_LEFT)
        
        self._draw_divider()
        
        # Assinatura
        self.y_pos -= (10 * mm)
        self._draw_line("_" * 40, "Courier", 8, TA_CENTER)
        self._draw_line("Assinatura do Operador/Supervisor", "Helvetica", 8, TA_CENTER)
        
        # Rodapé
        self.y_pos -= (5 * mm)
        op = self.full_data["operador"].get('username', 'N/A')
        self._draw_line(f"Cancelado por: {op}", "Helvetica", 8, TA_CENTER)
        self._draw_line(datetime.now().strftime("%d/%m/%Y %H:%M:%S"), "Helvetica", 8, TA_CENTER)
        
        return self._save_and_close_pdf()

def generate_and_print_receipt(sale_data_dict):
    """
    Função pública que orquestra a criação e impressão do CUPOM DE VENDA.
    """
    conn = None
    pdf_path = None
    try:
        conn = get_connection()
        printer = ReceiptPrinter(sale_data_dict)
        printer._load_full_data(conn)
        
        tipo = sale_data_dict.get('tipo_documento', 'FISCAL')
        n_venda = sale_data_dict['numero_venda_terminal']
        
        if tipo == 'NAO_FISCAL':
            pdf_path = printer._generate_non_fiscal_receipt()
            suggested_name = f"Cupom_NaoFiscal_{n_venda}.pdf"
        else: # FISCAL
            pdf_path = printer._generate_fiscal_receipt()
            suggested_name = f"Cupom_Fiscal_{n_venda}.pdf"

        if pdf_path:
            printer_name = _get_printer_name(conn, sale_data_dict['terminal_id'])
            if (not printer_name or any(v in printer_name.lower() for v in ["microsoft print to pdf", "xps", "onenote", "document writer"])):
                print(f"Impressora '{printer_name}' é virtual ou não definida. Usando 'Salvar Como'...")
                _save_virtual_pdf(pdf_path, suggested_name)
            else:
                print(f"Enviando para impressora física: {printer_name}")
                _print_physical(pdf_path, printer_name)
        
    except Exception as e:
        QMessageBox.critical(None, "Erro Fatal no Cupom", f"Ocorreu um erro geral: {e}")
    finally:
        if conn: conn.close()

# --- NOVA FUNÇÃO PÚBLICA: Imprimir Cancelamento ---
def generate_and_print_cancellation_receipt(sale_data_dict, motivo):
    """
    Gera e imprime o comprovante de cancelamento.
    """
    conn = None
    pdf_path = None
    try:
        conn = get_connection()
        printer = ReceiptPrinter(sale_data_dict)
        printer._load_full_data(conn) 
        
        pdf_path = printer._generate_cancellation_receipt(motivo)
        suggested_name = f"Cancelamento_Venda_{sale_data_dict['numero_venda_terminal']}.pdf"
        
        if pdf_path:
            printer_name = _get_printer_name(conn, sale_data_dict['terminal_id'])
            if (not printer_name or any(v in printer_name.lower() for v in ["microsoft print to pdf", "xps", "onenote", "document writer"])):
                _save_virtual_pdf(pdf_path, suggested_name)
            else:
                _print_physical(pdf_path, printer_name)
                
    except Exception as e:
        QMessageBox.critical(None, "Erro Fatal no Cancelamento", f"Erro ao imprimir comprovante: {e}")
    finally:
        if conn: conn.close()

# -------------------------------------------------------------------
# --- FUNÇÃO 2: IMPRESSÃO DE RELATÓRIO Z (Fechamento) ---
# -------------------------------------------------------------------

def generate_and_print_z_report(report_text, terminal_id):
    """
    Função pública que gera e imprime o Relatório Z (Sintético).
    """
    conn = None
    pdf_path = None
    try:
        conn = get_connection()
        printer_name = _get_printer_name(conn, terminal_id)
        
        fd, pdf_path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        
        # Altura dinâmica para o Relatório Z também
        num_lines = report_text.count('\n') + 10
        dynamic_height = num_lines * (5 * mm)
        
        doc = SimpleDocTemplate(pdf_path, pagesize=(WIDTH, dynamic_height),
                                leftMargin=MARGIN_LEFT, rightMargin=MARGIN_LEFT,
                                topMargin=5*mm, bottomMargin=5*mm)
        
        styles = getSampleStyleSheet()
        style = ParagraphStyle('ReportStyle', parent=styles['Normal'], fontName='Courier', fontSize=8, leading=10)
        formatted_text = report_text.replace(" ", "&nbsp;").replace("\n", "<br/>")
        story = [Paragraph(formatted_text, style)]
        doc.build(story)

        if pdf_path:
            suggested_name = f"Relatorio_Fechamento_{datetime.now():%Y%m%d}.pdf"
            if (not printer_name or any(v in printer_name.lower() for v in ["microsoft print to pdf", "xps", "onenote", "document writer"])):
                _save_virtual_pdf(pdf_path, suggested_name)
            else:
                _print_physical(pdf_path, printer_name)
                
    except Exception as e:
        QMessageBox.critical(None, "Erro Fatal no Relatório Z", f"Erro: {e}")
        if pdf_path and os.path.exists(pdf_path):
            os.remove(pdf_path)
            
    finally:
        if conn: conn.close()