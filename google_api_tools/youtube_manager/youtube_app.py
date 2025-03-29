import os
import json
import logging
import time
from typing import Dict, List, Optional, Any, Tuple, Union
import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from data_processor import DataProcessor
from ai_responder import YouTubeAIResponder
from config import CONFIG

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='youtube_ai.log'
)
logger = logging.getLogger('youtube_app')

# Configuração da API do YouTube
SCOPES = CONFIG['youtube']['scopes']
API_SERVICE_NAME = CONFIG['youtube']['api_service_name']
API_VERSION = CONFIG['youtube']['api_version']
CLIENT_SECRETS_FILE = CONFIG['youtube']['client_secrets_file']

class YouTubeApp:
    def __init__(self):
        self.youtube = None
        self.channel_id = None
        self.channel_info = None
        self.data_processor = DataProcessor()
        self.ai_responder = None
        self.videos_cache: Dict[str, Dict[str, Any]] = {}
        logger.info("YouTubeApp inicializado")
        
    def authenticate(self) -> bool:
        """
        Autentica com a API do YouTube
        
        Returns:
            True se autenticação bem-sucedida, False caso contrário
        """
        try:
            logger.info("Iniciando autenticação com YouTube API")
            
            # Verificar se o arquivo de credenciais existe
            if not os.path.exists(CLIENT_SECRETS_FILE):
                logger.error(f"Arquivo de credenciais não encontrado: {CLIENT_SECRETS_FILE}")
                print(f"Erro: Arquivo de credenciais não encontrado: {CLIENT_SECRETS_FILE}")
                return False
                
            # For development/testing, we need to allow unverified apps
            os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
            os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
            
            print("\nIniciando fluxo de autenticação...")
            print("Uma janela do navegador será aberta para autorização.")
            print("NOTA: Você verá um aviso de 'App não verificado' - isso é esperado durante o desenvolvimento.")
            print("      Clique em 'Avançar' e depois em 'Continuar' para prosseguir com o teste.")
            
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRETS_FILE, SCOPES)
            # Forçar a tela de consentimento e adicionar acesso offline
            credentials = flow.run_local_server(
                port=8080, 
                prompt='consent',
                access_type='offline'
            )
            
            self.youtube = googleapiclient.discovery.build(
                API_SERVICE_NAME, API_VERSION, credentials=credentials)
                
            logger.info("Autenticação com YouTube API concluída com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro na autenticação: {str(e)}")
            print(f"Erro na autenticação: {str(e)}")
            return False
        
    def get_channel_info(self) -> Dict[str, Any]:
        """
        Obtém informações do canal autenticado
        
        Returns:
            Dicionário com informações do canal
            
        Raises:
            Exception: Se não estiver autenticado ou canal não for encontrado
        """
        if not self.youtube:
            logger.error("Tentativa de obter informações do canal sem autenticação")
            raise Exception("É necessário autenticar primeiro")
            
        try:
            logger.info("Obtendo informações do canal")
            response = self.youtube.channels().list(
                part='snippet,statistics,contentDetails',
                mine=True
            ).execute()
            
            if not response.get('items'):
                logger.error("Canal não encontrado na resposta da API")
                raise Exception("Não foi possível encontrar o canal")
                
            self.channel_info = response['items'][0]
            self.channel_id = self.channel_info['id']
            
            logger.info(f"Informações do canal obtidas: {self.channel_info['snippet']['title']}")
            return self.channel_info
            
        except googleapiclient.errors.HttpError as e:
            error_msg = f"Erro ao obter informações do canal: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
    def get_channel_videos(self, max_results: int = None) -> List[Dict[str, Any]]:
        """
        Obtém vídeos do canal com suporte a paginação
        
        Args:
            max_results: Número máximo de resultados (usa configuração padrão se None)
                         Se None, tenta obter todos os vídeos do canal
            
        Returns:
            Lista de vídeos do canal
        """
        if max_results is None:
            # Se não especificado, tentamos obter todos os vídeos
            # Usamos o total de vídeos do canal como referência
            if self.channel_info and 'statistics' in self.channel_info:
                max_results = int(self.channel_info['statistics'].get('videoCount', 50))
            else:
                max_results = CONFIG['app']['default_max_results']
            
        if not self.channel_id:
            logger.info("Channel ID não encontrado, obtendo informações do canal")
            self.get_channel_info()
            
        logger.info(f"Obtendo até {max_results} vídeos do canal {self.channel_id}")
        
        try:
            videos = []
            next_page_token = None
            page_size = 50  # Máximo permitido pela API do YouTube
            
            # Continua buscando páginas até atingir o máximo ou não ter mais resultados
            while len(videos) < max_results:
                # Calcula quantos itens ainda precisamos buscar
                remaining = min(page_size, max_results - len(videos))
                
                request = self.youtube.search().list(
                    part="id,snippet",
                    channelId=self.channel_id,
                    maxResults=remaining,
                    pageToken=next_page_token,
                    type="video",
                    order="date"
                )
                response = request.execute()
                
                for item in response.get('items', []):
                    if 'id' not in item or 'videoId' not in item['id']:
                        continue
                        
                    video_id = item['id']['videoId']
                    self.videos_cache[video_id] = {
                        'title': item['snippet'].get('title', 'Sem título'),
                        'description': item['snippet'].get('description', ''),
                        'published_at': item['snippet'].get('publishedAt', '')
                    }
                    videos.append({
                        'video_id': video_id,
                        'title': item['snippet'].get('title', 'Sem título'),
                        'published_at': item['snippet'].get('publishedAt', '')
                    })
                
                # Verifica se há mais páginas
                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    break
                    
                # Pequena pausa para evitar limites de taxa da API
                time.sleep(0.2)
                
            logger.info(f"Obtidos {len(videos)} vídeos do canal")
            return videos
            
        except googleapiclient.errors.HttpError as e:
            logger.error(f"Erro ao obter vídeos do canal: {str(e)}")
            return []
        
    def get_video_comments(self, video_id: str, max_results: int = None) -> List[Dict[str, Any]]:
        """
        Obtém comentários de um vídeo específico
        
        Args:
            video_id: ID do vídeo
            max_results: Número máximo de resultados (usa configuração padrão se None)
            
        Returns:
            Lista de comentários do vídeo
        """
        if max_results is None:
            max_results = CONFIG['app']['default_max_comments']
            
        logger.info(f"Obtendo até {max_results} comentários do vídeo {video_id}")
        
        try:
            comments_request = self.youtube.commentThreads().list(
                part="snippet,replies",
                videoId=video_id,
                maxResults=max_results
            )
            comments_response = comments_request.execute()
            
            comments = []
            for comment_item in comments_response.get('items', []):
                # Comentário principal
                comment_id = comment_item['id']
                top_comment = comment_item['snippet']['topLevelComment']['snippet']
                
                comment_info = {
                    'comment_id': comment_id,
                    'video_id': video_id,
                    'author': top_comment['authorDisplayName'],
                    'author_channel_id': top_comment.get('authorChannelId', {}).get('value', ''),
                    'text': top_comment['textDisplay'],
                    'like_count': top_comment['likeCount'],
                    'published_at': top_comment['publishedAt']
                }
                comments.append(comment_info)
                
                # Respostas ao comentário
                if 'replies' in comment_item:
                    for reply in comment_item['replies']['comments']:
                        reply_snippet = reply['snippet']
                        reply_info = {
                            'comment_id': reply['id'],
                            'video_id': video_id,
                            'parent_id': comment_id,
                            'author': reply_snippet['authorDisplayName'],
                            'author_channel_id': reply_snippet.get('authorChannelId', {}).get('value', ''),
                            'text': reply_snippet['textDisplay'],
                            'like_count': reply_snippet['likeCount'],
                            'published_at': reply_snippet['publishedAt']
                        }
                        comments.append(reply_info)
                        
            logger.info(f"Obtidos {len(comments)} comentários do vídeo {video_id}")
            return comments
                
        except googleapiclient.errors.HttpError as e:
            logger.error(f"Erro ao obter comentários para o vídeo {video_id}: {str(e)}")
            return []
            
    def get_all_channel_comments(self) -> List[Dict[str, Any]]:
        """
        Obtém todos os comentários de todos os vídeos do canal
        
        Returns:
            Lista com todos os comentários
        """
        logger.info("Iniciando coleta de todos os comentários do canal")
        videos = self.get_channel_videos()
        all_comments = []
        
        for i, video in enumerate(videos):
            video_id = video['video_id']
            print(f"Obtendo comentários do vídeo ({i+1}/{len(videos)}): {video['title']}")
            logger.info(f"Obtendo comentários do vídeo {i+1}/{len(videos)}: {video_id}")
            
            comments = self.get_video_comments(video_id)
            all_comments.extend(comments)
            
            # Pequena pausa para evitar limites de taxa da API
            time.sleep(0.5)
            
        logger.info(f"Total de {len(all_comments)} comentários coletados de {len(videos)} vídeos")
        self.data_processor.load_comments(all_comments)
        return all_comments
        
    def get_unanswered_comments(self) -> List[Dict[str, Any]]:
        """
        Obtém comentários sem respostas do canal
        
        Returns:
            Lista de comentários sem respostas
        """
        logger.info("Buscando comentários sem respostas")
        
        # Primeiro, obtemos todos os comentários
        all_comments = self.get_all_channel_comments()
        
        # Identificamos os IDs de comentários que têm respostas
        answered_ids = set()
        for comment in all_comments:
            if 'parent_id' in comment:
                answered_ids.add(comment['parent_id'])
        
        # Filtramos apenas os comentários principais (não respostas) que não têm respostas
        unanswered_comments = [
            comment for comment in all_comments 
            if 'parent_id' not in comment and comment['comment_id'] not in answered_ids
        ]
        
        logger.info(f"Encontrados {len(unanswered_comments)} comentários sem respostas")
        return unanswered_comments
    
    def reply_to_comment(self, comment_id: str, text: str) -> Tuple[bool, Union[Dict[str, Any], str]]:
        """
        Responde a um comentário no YouTube
        
        Args:
            comment_id: ID do comentário a responder
            text: Texto da resposta
            
        Returns:
            Tupla com (sucesso, resposta/erro)
        """
        if not text or not comment_id:
            logger.error("Tentativa de responder com texto vazio ou ID de comentário inválido")
            return False, "Texto de resposta ou ID de comentário inválido"
            
        logger.info(f"Respondendo ao comentário {comment_id}")
        
        try:
            response = self.youtube.comments().insert(
                part="snippet",
                body={
                    "snippet": {
                        "parentId": comment_id,
                        "textOriginal": text
                    }
                }
            ).execute()
            
            logger.info(f"Resposta publicada com sucesso ao comentário {comment_id}")
            return True, response
            
        except googleapiclient.errors.HttpError as e:
            error_msg = str(e)
            logger.error(f"Erro ao responder comentário {comment_id}: {error_msg}")
            return False, error_msg
    
    def setup_ai_responder(self, api_key: Optional[str] = None) -> YouTubeAIResponder:
        """
        Configura o respondedor de IA
        
        Args:
            api_key: Chave de API OpenAI (opcional)
            
        Returns:
            Instância configurada do YouTubeAIResponder
        """
        logger.info("Configurando AI Responder")
        
        try:
            model = CONFIG['openai'].get('model', 'gpt-4o')
            self.ai_responder = YouTubeAIResponder(model=model, api_key=api_key)
            logger.info(f"AI Responder configurado com modelo {model}")
            return self.ai_responder
            
        except Exception as e:
            logger.error(f"Erro ao configurar AI Responder: {str(e)}")
            raise
    
    def auto_respond_to_comments(self, comments: Optional[List[Dict[str, Any]]] = None, 
                                max_responses: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Responde automaticamente a comentários usando IA
        
        Args:
            comments: Lista de comentários (obtém todos se None)
            max_responses: Número máximo de respostas (usa configuração padrão se None)
            
        Returns:
            Lista de resultados das respostas
            
        Raises:
            Exception: Se o AI Responder não estiver configurado
        """
        if not self.ai_responder:
            logger.error("Tentativa de responder automaticamente sem configurar AI Responder")
            raise Exception("É necessário configurar o AI Responder primeiro")
            
        if max_responses is None:
            max_responses = CONFIG['app']['default_max_responses']
            
        logger.info(f"Iniciando resposta automática para até {max_responses} comentários")
            
        if not comments:
            logger.info("Nenhum comentário fornecido, obtendo todos os comentários do canal")
            comments = self.get_all_channel_comments()
            
        # Filtra apenas comentários principais (não respostas)
        main_comments = [c for c in comments if 'parent_id' not in c]
        logger.info(f"Filtrados {len(main_comments)} comentários principais de {len(comments)} totais")
        
        # Limita o número de respostas
        comments_to_respond = main_comments[:max_responses]
        logger.info(f"Respondendo a {len(comments_to_respond)} comentários")
        
        results = []
        for i, comment in enumerate(comments_to_respond):
            logger.info(f"Processando comentário {i+1}/{len(comments_to_respond)}")
            
            video_title = None
            if comment['video_id'] in self.videos_cache:
                video_title = self.videos_cache[comment['video_id']]['title']
                
            # Gera resposta com IA
            ai_response = self.ai_responder.generate_response(
                comment, 
                self.channel_info, 
                video_title
            )
            
            if ai_response['success']:
                logger.info(f"Resposta gerada com sucesso, publicando no YouTube")
                # Publica resposta no YouTube
                success, response = self.reply_to_comment(
                    comment['comment_id'], 
                    ai_response['response']
                )
                
                result = {
                    'comment': comment,
                    'ai_response': ai_response['response'],
                    'posted': success,
                    'response_data': response if success else None
                }
                results.append(result)
                
                # Pequena pausa para evitar limites de taxa da API
                time.sleep(1)
            else:
                logger.warning(f"Falha ao gerar resposta para comentário {comment['comment_id']}")
                
        logger.info(f"Resposta automática concluída. {len(results)} respostas publicadas")
        return results
    
    def prepare_training_data(self) -> Dict[str, Any]:
        """
        Prepara dados para fine-tuning
        
        Returns:
            Dicionário com contagem e nome do arquivo
        """
        logger.info("Preparando dados para fine-tuning")
        
        comments = self.get_all_channel_comments()
        self.data_processor.load_comments(comments)
        
        count = self.data_processor.prepare_for_finetuning()
        filename = self.data_processor.export_training_data()
        
        result = {
            'count': count,
            'filename': filename
        }
        
        logger.info(f"Dados de treinamento preparados: {count} exemplos em {filename}")
        return result
    
def check_environment():
    """Verifica se o ambiente está configurado corretamente"""
    issues = []
    
    # Verificar chave de API da OpenAI
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        issues.append("Variável de ambiente OPENAI_API_KEY não encontrada")
    
    # Verificar arquivo de credenciais do YouTube
    if not os.path.exists(CLIENT_SECRETS_FILE):
        issues.append(f"Arquivo de credenciais do YouTube não encontrado: {CLIENT_SECRETS_FILE}")
    
    # Verificar se o app está em modo de desenvolvimento
    print("NOTA: Aplicativo configurado para desenvolvimento/teste.")
    print("      Isso permite o uso sem verificação completa do Google.")
    
    return issues

def main():
    # Tentar carregar variáveis de ambiente do arquivo .env se existir
    try:
        from dotenv import load_dotenv
        load_dotenv()
        logger.info("Variáveis de ambiente carregadas do arquivo .env")
    except ImportError:
        logger.warning("Módulo dotenv não encontrado. Variáveis de ambiente não serão carregadas do arquivo .env")
    
    app = YouTubeApp()
    
    print("\n--- Aplicativo de Gerenciamento de Canal do YouTube com IA ---")
    
    # Verificar ambiente
    issues = check_environment()
    if issues:
        print("\n⚠️ Problemas de configuração detectados:")
        for issue in issues:
            print(f"  - {issue}")
        print("\nAlgumas funcionalidades podem não funcionar corretamente.")
    
    print("\nIniciando autenticação com o YouTube...")
    
    try:
        if not app.authenticate():
            print("\nFalha na autenticação. Verifique suas credenciais e tente novamente.")
            return
            
        channel_info = app.get_channel_info()
        print(f"\nAutenticado com sucesso no canal: {channel_info['snippet']['title']}")
        
        while True:
            print("\n--- Menu Principal ---")
            print("1. Ver estatísticas do canal")
            print("2. Ver todos os vídeos do canal")
            print("3. Ver todos os comentários do canal")
            print("4. Ver comentários sem respostas")
            print("5. Preparar dados para fine-tuning")
            print("6. Configurar respondedor de IA")
            print("7. Responder comentários automaticamente com IA")
            print("8. Exportar dados para análise")
            print("9. Sair")
            
            choice = input("\nEscolha uma opção: ")
            
            if choice == '1':
                # Ver estatísticas do canal
                stats = app.channel_info
                print("\n=== Estatísticas do Canal ===")
                print(f"Nome: {stats['snippet']['title']}")
                print(f"Descrição: {stats['snippet']['description']}")
                print(f"URL: https://youtube.com/channel/{stats['id']}")
                print(f"Inscritos: {stats['statistics']['subscriberCount']}")
                print(f"Total de visualizações: {stats['statistics']['viewCount']}")
                print(f"Total de vídeos: {stats['statistics']['videoCount']}")
                
            elif choice == '2':
                # Ver todos os vídeos do canal
                videos = app.get_channel_videos()
                print(f"\n=== {len(videos)} Vídeos Encontrados ===")
                for i, video in enumerate(videos, 1):
                    print(f"\n{i}. {video['title']}")
                    print(f"   ID: {video['video_id']}")
                    print(f"   URL: https://youtube.com/watch?v={video['video_id']}")
                    print(f"   Publicado em: {video['published_at']}")
            
            elif choice == '3':
                # Ver todos os comentários do canal
                comments = app.get_all_channel_comments()
                print(f"\n=== {len(comments)} Comentários Encontrados ===")
                for i, comment in enumerate(comments[:20], 1):  # Mostrar primeiros 20
                    is_reply = 'parent_id' in comment
                    print(f"\n{i}. {'(Resposta) ' if is_reply else ''}{comment['author']}: {comment['text'][:100]}...")
                    print(f"   Vídeo: {comment['video_id']}")
                    print(f"   Likes: {comment['like_count']}")
                    print(f"   Data: {comment['published_at']}")
                
                if len(comments) > 20:
                    print(f"\n... e mais {len(comments) - 20} comentários.")
            
            elif choice == '4':
                # Ver comentários sem respostas
                print("\nBuscando comentários sem respostas...")
                unanswered = app.get_unanswered_comments()
                print(f"\n=== {len(unanswered)} Comentários Sem Respostas ===")
                
                for i, comment in enumerate(unanswered[:20], 1):  # Mostrar primeiros 20
                    print(f"\n{i}. {comment['author']}: {comment['text'][:100]}...")
                    print(f"   Vídeo: {comment['video_id']}")
                    if comment['video_id'] in app.videos_cache:
                        print(f"   Título do vídeo: {app.videos_cache[comment['video_id']]['title']}")
                    print(f"   Likes: {comment['like_count']}")
                    print(f"   Data: {comment['published_at']}")
                
                if len(unanswered) > 20:
                    print(f"\n... e mais {len(unanswered) - 20} comentários sem respostas.")
                    
                if len(unanswered) > 0:
                    respond_choice = input("\nDeseja responder a algum destes comentários? (s/n): ")
                    if respond_choice.lower() == 's':
                        if not app.ai_responder:
                            setup_ai = input("Respondedor de IA não configurado. Configurar agora? (s/n): ")
                            if setup_ai.lower() == 's':
                                api_key = os.getenv("OPENAI_API_KEY")
                                app.setup_ai_responder(api_key)
                            else:
                                continue
                                
                        try:
                            comment_num = int(input("Digite o número do comentário que deseja responder: "))
                            if 1 <= comment_num <= len(unanswered):
                                selected = unanswered[comment_num-1]
                                
                                # Gerar resposta com IA
                                video_title = None
                                if selected['video_id'] in app.videos_cache:
                                    video_title = app.videos_cache[selected['video_id']]['title']
                                    
                                ai_response = app.ai_responder.generate_response(
                                    selected, 
                                    app.channel_info, 
                                    video_title
                                )
                                
                                if ai_response['success']:
                                    print(f"\nResposta gerada: {ai_response['response']}")
                                    post_choice = input("Publicar esta resposta? (s/n): ")
                                    
                                    if post_choice.lower() == 's':
                                        success, response = app.reply_to_comment(
                                            selected['comment_id'], 
                                            ai_response['response']
                                        )
                                        
                                        if success:
                                            print("Resposta publicada com sucesso!")
                                        else:
                                            print(f"Erro ao publicar resposta: {response}")
                                else:
                                    print(f"Erro ao gerar resposta: {ai_response['error']}")
                            else:
                                print("Número de comentário inválido.")
                        except ValueError:
                            print("Por favor, digite um número válido.")
            
            elif choice == '5':
                # Preparar dados para fine-tuning
                print("\nPreparando dados para fine-tuning...")
                result = app.prepare_training_data()
                print(f"\nDados preparados com sucesso!")
                print(f"Total de exemplos de treinamento: {result['count']}")
                print(f"Arquivo salvo em: {result['filename']}")
                print("\nVocê pode usar este arquivo para fazer fine-tuning em um modelo de IA.")
                print("Isto permitirá que o modelo aprenda seu estilo de resposta e o contexto do seu canal.")
            
            elif choice == '6':
                # Configurar respondedor de IA
                print("\n=== Configuração do Respondedor de IA ===")
                api_key = os.getenv("OPENAI_API_KEY")
                
                if not api_key:
                    use_key = input("Chave de API OpenAI não encontrada no ambiente. Deseja fornecer uma? (s/n): ")
                    if use_key.lower() == 's':
                        api_key = input("Digite sua chave de API OpenAI: ")
                
                try:
                    app.setup_ai_responder(api_key)
                    print("Respondedor de IA configurado com sucesso!")
                except Exception as e:
                    print(f"Erro ao configurar respondedor de IA: {e}")
            
            elif choice == '7':
                # Responder comentários automaticamente
                if not app.ai_responder:
                    print("\nVocê precisa configurar o respondedor de IA primeiro (opção 6).")
                    continue
                    
                print("\n=== Responder Comentários Automaticamente ===")
                max_resp = input("Número máximo de comentários para responder automaticamente: ")
                try:
                    max_resp = int(max_resp)
                    if max_resp <= 0:
                        raise ValueError("O número deve ser positivo")
                except ValueError:
                    print("Por favor, digite um número válido.")
                    continue
                
                print(f"\nResponder automaticamente a até {max_resp} comentários? Esta ação publicará respostas no YouTube.")
                confirm = input("Confirmar? (s/n): ")
                
                if confirm.lower() == 's':
                    print("\nGerando e publicando respostas...")
                    results = app.auto_respond_to_comments(max_responses=max_resp)
                    
                    # Mostrar resultados
                    success_count = sum(1 for r in results if r['posted'])
                    print(f"\nRespostas publicadas com sucesso: {success_count} de {len(results)}")
                    
                    for i, result in enumerate(results, 1):
                        status = "✓ Publicado" if result['posted'] else "✗ Falha"
                        print(f"\n{i}. {status}")
                        print(f"   Comentário: {result['comment']['text'][:100]}...")
                        print(f"   Resposta IA: {result['ai_response']}")
            
            elif choice == '8':
                # Exportar dados para análise
                print("\n=== Exportar Dados para Análise ===")
                print("1. Exportar comentários para CSV")
                print("2. Exportar dados de treinamento para JSONL")
                print("3. Exportar histórico de interações de IA")
                print("4. Voltar")
                
                export_choice = input("\nEscolha uma opção: ")
                
                if export_choice == '1':
                    filename = app.data_processor.export_to_csv()
                    print(f"Dados exportados para {filename}")
                    
                elif export_choice == '2':
                    app.prepare_training_data()
                    filename = app.data_processor.export_training_data()
                    print(f"Dados exportados para {filename}")
                    
                elif export_choice == '3':
                    if not app.ai_responder:
                        print("Respondedor de IA não configurado.")
                        continue
                        
                    filename = app.ai_responder.export_interaction_history()
                    print(f"Histórico de interações exportado para {filename}")
            
            elif choice == '9':
                print("\nSaindo do aplicativo. Até mais!")
                break
                
            else:
                print("\nOpção inválida. Tente novamente.")
    
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == '__main__':
    main()
