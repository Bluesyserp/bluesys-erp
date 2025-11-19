import requests
import os
import sys
import logging
import subprocess
from PyQt5.QtWidgets import QMessageBox

# Configurações
CURRENT_VERSION = "1.0.0"
REPO_OWNER = "seu-usuario-github"  # Troque pelo seu
REPO_NAME = "bluesys-erp"          # Troque pelo seu
GITHUB_API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"

def check_for_update():
    """
    Verifica se há uma nova versão no GitHub.
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Em um sistema real, você deve tratar autenticação se o repo for privado
        # Para repos públicos, isso funciona direto.
        response = requests.get(GITHUB_API_URL, timeout=5)
        
        if response.status_code == 200:
            release_data = response.json()
            latest_version = release_data["tag_name"].replace("v", "") # Ex: v1.0.1 -> 1.0.1
            
            if is_newer(latest_version, CURRENT_VERSION):
                logger.info(f"Nova versão encontrada: {latest_version}")
                
                reply = QMessageBox.question(
                    None, 
                    "Atualização Disponível",
                    f"Uma nova versão ({latest_version}) está disponível.\n"
                    "Deseja atualizar agora?",
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    download_url = release_data["assets"][0]["browser_download_url"]
                    perform_update(download_url, latest_version)
                    
        else:
            logger.warning(f"Não foi possível checar atualizações. Status: {response.status_code}")
            
    except Exception as e:
        logger.error(f"Erro ao verificar atualizações: {e}")

def is_newer(v_remote, v_local):
    # Lógica simples de comparação de versão (ex: 1.0.1 > 1.0.0)
    return v_remote > v_local

def perform_update(download_url, version):
    # Aqui entraria a lógica de baixar o .exe, renomear o atual para .old
    # e salvar o novo.
    # Isso geralmente requer um segundo executável (um "launcher") 
    # porque o programa não pode se substituir enquanto está rodando.
    QMessageBox.information(None, "Atualização", 
        f"O sistema baixaria a versão {version} agora.\n(Lógica de download a implementar)")
    # Em produção, você baixa o arquivo, e chama um script .bat para trocar os arquivos e reiniciar.