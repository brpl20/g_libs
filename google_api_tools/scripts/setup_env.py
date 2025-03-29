"""
Environment setup script for YouTube AI Responder
This script helps set up the environment for testing the YouTube AI Responder
"""
import os
import json
import sys
from dotenv import load_dotenv

def setup_environment():
    """Set up the environment for testing"""
    print("\n=== Configuração do Ambiente para YouTube AI Responder ===")
    
    # Load environment variables from .env file
    try:
        load_dotenv()
        print("✅ Variáveis de ambiente carregadas do arquivo .env")
    except Exception as e:
        print(f"⚠️ Erro ao carregar variáveis de ambiente: {e}")
    
    # Check for OpenAI API key
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("\n⚠️ Chave de API OpenAI não encontrada no ambiente.")
        key = input("Digite sua chave de API OpenAI (ou pressione Enter para pular): ")
        if key:
            # Set for current session
            os.environ["OPENAI_API_KEY"] = key
            print("✅ Chave de API OpenAI definida para esta sessão")
            
            # Ask if user wants to save to .env file
            save = input("Deseja salvar esta chave em um arquivo .env? (s/n): ")
            if save.lower() == 's':
                with open('.env', 'w') as f:
                    f.write(f"OPENAI_API_KEY={key}\n")
                print("✅ Chave salva no arquivo .env")
    else:
        print("✅ Chave de API OpenAI encontrada no ambiente")
    
    # Check for YouTube credentials
    client_secrets_file = "client_secret.json"
    if not os.path.exists(client_secrets_file):
        print(f"\n⚠️ Arquivo de credenciais do YouTube não encontrado: {client_secrets_file}")
        print("Você precisará de um arquivo de credenciais do YouTube para autenticação completa.")
        print("Visite https://console.developers.google.com/ para criar credenciais OAuth.")
        
        # Create a dummy file for testing if user wants
        create_dummy = input("Deseja criar um arquivo de credenciais fictício para testes? (s/n): ")
        if create_dummy.lower() == 's':
            dummy_credentials = {
                "installed": {
                    "client_id": "dummy-client-id.apps.googleusercontent.com",
                    "project_id": "youtube-ai-responder",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_secret": "dummy-client-secret",
                    "redirect_uris": ["http://localhost"]
                }
            }
            with open(client_secrets_file, 'w') as f:
                json.dump(dummy_credentials, f, indent=2)
            print(f"✅ Arquivo de credenciais fictício criado: {client_secrets_file}")
            print("⚠️ Este arquivo é apenas para testes e não funcionará para autenticação real.")
    else:
        print(f"✅ Arquivo de credenciais do YouTube encontrado: {client_secrets_file}")
    
    # Create config file if it doesn't exist
    config_file = "youtube_ai_config.json"
    if not os.path.exists(config_file):
        print(f"\n⚠️ Arquivo de configuração não encontrado: {config_file}")
        create_config = input("Deseja criar um arquivo de configuração padrão? (s/n): ")
        if create_config.lower() == 's':
            default_config = {
                "openai": {
                    "model": "gpt-4o",
                    "temperature": 0.7,
                    "max_tokens": 150
                },
                "youtube": {
                    "api_service_name": "youtube",
                    "api_version": "v3",
                    "client_secrets_file": client_secrets_file,
                    "scopes": ["https://www.googleapis.com/auth/youtube.force-ssl"]
                },
                "app": {
                    "default_max_results": 50,
                    "default_max_comments": 100,
                    "default_max_responses": 10
                }
            }
            with open(config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
            print(f"✅ Arquivo de configuração criado: {config_file}")
    else:
        print(f"✅ Arquivo de configuração encontrado: {config_file}")
    
    print("\n✅ Configuração do ambiente concluída!")
    return True

if __name__ == "__main__":
    setup_environment()
