import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from openai import OpenAI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='youtube_ai.log'
)
logger = logging.getLogger('ai_responder')

class YouTubeAIResponder:
    def __init__(self, model: str = "gpt-4o", api_key: Optional[str] = None):
        """
        Inicializa o respondedor de IA para YouTube
        
        Args:
            model: Modelo a ser utilizado (padrão gpt-4o)
            api_key: Chave de API do OpenAI (ou usa a variável de ambiente OPENAI_API_KEY)
        """
        self.model = model
        
        # Configurar API key (prioriza o parâmetro, depois variável de ambiente)
        api_key = api_key or os.getenv("OPENAI_API_KEY")
            
        if not api_key:
            raise ValueError("API key não encontrada. Defina OPENAI_API_KEY ou passe como parâmetro.")
        
        # Inicializar cliente OpenAI
        self.client = OpenAI(api_key=api_key)
            
        # Histórico de interações para análise
        self.interaction_history: List[Dict[str, Any]] = []
        
        # Carregar model de treino customizado se existir
        self.custom_model = os.getenv("YOUTUBE_CUSTOM_MODEL")
        if self.custom_model:
            logger.info(f"Usando modelo customizado: {self.custom_model}")
            self.model = self.custom_model
            
    def _get_channel_context(self, channel_stats: Optional[Dict[str, Any]]) -> str:
        """
        Cria um contexto sobre o canal para melhorar as respostas
        
        Args:
            channel_stats: Dicionário com estatísticas do canal
            
        Returns:
            String formatada com informações do canal
        """
        if not channel_stats:
            return "Canal: Meu Canal\nDescrição: Canal de conteúdo no YouTube"
            
        return f"""
        Canal: {channel_stats.get('snippet', {}).get('title', 'Meu Canal')}
        Descrição: {channel_stats.get('snippet', {}).get('description', 'Canal de conteúdo no YouTube')}
        Inscritos: {channel_stats.get('statistics', {}).get('subscriberCount', 'N/A')}
        Total de vídeos: {channel_stats.get('statistics', {}).get('videoCount', 'N/A')}
        """
        
    def generate_response(self, comment: Dict[str, Any], 
                         channel_stats: Optional[Dict[str, Any]] = None, 
                         video_title: Optional[str] = None) -> Dict[str, Any]:
        """
        Gera uma resposta personalizada para um comentário do YouTube
        
        Args:
            comment: Dicionário com informações do comentário
            channel_stats: Estatísticas do canal para contexto (opcional)
            video_title: Título do vídeo do comentário (opcional)
            
        Returns:
            Dicionário com a resposta gerada e status de sucesso
        """
        # Construir o prompt para o modelo
        system_prompt = """Você é um assistente que responde comentários de YouTube de forma amigável e pessoal.
        Responda como se fosse o dono do canal, de forma breve e engajante.
        Evite respostas genéricas. Agradeça pelos elogios específicos e responda perguntas de forma útil.
        Mantenha as respostas entre 1-3 frases para manter um tom conversacional natural."""
        
        # Adicionar contexto se disponível
        if channel_stats:
            channel_context = self._get_channel_context(channel_stats)
            system_prompt += f"\n\nInformações do Canal:\n{channel_context}"
            
        if video_title:
            system_prompt += f"\n\nComentário no vídeo: {video_title}"
        
        # Extrair informações do comentário
        comment_text = comment.get('text', '')
        author_name = comment.get('author', 'Usuário')
        
        try:
            logger.info(f"Gerando resposta para comentário de {author_name}")
            
            # Chamada à API do modelo com o novo cliente OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Comentário de {author_name}: {comment_text}"}
                ],
                max_tokens=150,
                temperature=0.7
            )
            
            # Extrair resposta
            ai_response = response.choices[0].message.content.strip()
            
            # Registrar interação para análise
            interaction_data = {
                "timestamp": datetime.now().isoformat(),
                "comment_author": author_name,
                "comment_text": comment_text,
                "ai_response": ai_response,
                "video_title": video_title,
                "model_used": self.model
            }
            self.interaction_history.append(interaction_data)
            
            logger.info(f"Resposta gerada com sucesso: {ai_response[:50]}...")
            
            return {
                "success": True,
                "response": ai_response
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar resposta: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "response": "Não foi possível gerar uma resposta automática para este comentário."
            }
    
    def bulk_respond(self, comments_list: List[Dict[str, Any]], 
                    channel_stats: Optional[Dict[str, Any]] = None, 
                    video_data: Optional[Dict[str, Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """
        Gera respostas para vários comentários de uma vez
        
        Args:
            comments_list: Lista de comentários para responder
            channel_stats: Estatísticas do canal (opcional)
            video_data: Dicionário com informações de vídeos (opcional)
            
        Returns:
            Lista de resultados com as respostas geradas
        """
        results = []
        total_comments = len(comments_list)
        
        logger.info(f"Iniciando resposta em massa para {total_comments} comentários")
        
        for i, comment in enumerate(comments_list):
            video_title = None
            if video_data and comment.get('video_id') in video_data:
                video_title = video_data[comment['video_id']].get('title')
                
            logger.info(f"Processando comentário {i+1}/{total_comments}")
            response_data = self.generate_response(comment, channel_stats, video_title)
            
            results.append({
                "comment": comment,
                "response": response_data.get("response"),
                "success": response_data.get("success", False)
            })
            
        logger.info(f"Resposta em massa concluída. Sucessos: {sum(1 for r in results if r['success'])}/{total_comments}")
        return results
    
    def export_interaction_history(self, filename: str = 'ai_interactions.jsonl') -> str:
        """
        Exporta histórico de interações para análise e melhoria
        
        Args:
            filename: Nome do arquivo para salvar o histórico
            
        Returns:
            Nome do arquivo salvo
        """
        logger.info(f"Exportando {len(self.interaction_history)} interações para {filename}")
        
        with open(filename, 'w', encoding='utf-8') as f:
            for interaction in self.interaction_history:
                f.write(json.dumps(interaction, ensure_ascii=False) + '\n')
                
        return filename
