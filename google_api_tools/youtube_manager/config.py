"""
Arquivo de configuração para o aplicativo YouTube AI Responder
"""
import os
from typing import Dict, Any
import json
import logging

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='youtube_ai.log'
)
logger = logging.getLogger('config')

# Arquivo de configuração
CONFIG_FILE = 'youtube_ai_config.json'

# Configurações padrão
DEFAULT_CONFIG = {
    "openai": {
        "model": "gpt-4o",
        "temperature": 0.7,
        "max_tokens": 150
    },
    "youtube": {
        "api_service_name": "youtube",
        "api_version": "v3",
        "client_secrets_file": "client_secret.json",
        "scopes": ["https://www.googleapis.com/auth/youtube.force-ssl"]
    },
    "app": {
        "default_max_results": 50,
        "default_max_comments": 100,
        "default_max_responses": 10
    }
}

def load_config() -> Dict[str, Any]:
    """
    Carrega configurações do arquivo ou usa padrões
    
    Returns:
        Dicionário com configurações
    """
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                logger.info(f"Configurações carregadas de {CONFIG_FILE}")
                return config
        except Exception as e:
            logger.error(f"Erro ao carregar configurações: {str(e)}")
    
    # Se não conseguir carregar, usa configurações padrão
    logger.info("Usando configurações padrão")
    return DEFAULT_CONFIG

def save_config(config: Dict[str, Any]) -> bool:
    """
    Salva configurações em arquivo
    
    Args:
        config: Dicionário com configurações para salvar
        
    Returns:
        True se salvou com sucesso, False caso contrário
    """
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        logger.info(f"Configurações salvas em {CONFIG_FILE}")
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar configurações: {str(e)}")
        return False

# Carrega configurações ao importar o módulo
CONFIG = load_config()
