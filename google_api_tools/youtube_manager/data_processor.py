import json
import pandas as pd
import re
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='youtube_ai.log'
)
logger = logging.getLogger('data_processor')

class DataProcessor:
    def __init__(self):
        self.comments_data: List[Dict[str, Any]] = []
        self.training_data: List[Dict[str, Any]] = []
    
    def load_comments(self, comments_list: List[Dict[str, Any]]) -> int:
        """
        Carrega comentários da API do YouTube
        
        Args:
            comments_list: Lista de comentários para carregar
            
        Returns:
            Número de comentários carregados
        """
        logger.info(f"Carregando {len(comments_list)} comentários")
        self.comments_data = comments_list
        return len(self.comments_data)
    
    def clean_text(self, text: str) -> str:
        """
        Limpa o texto removendo HTML e caracteres especiais
        
        Args:
            text: Texto a ser limpo
            
        Returns:
            Texto limpo
        """
        if not text:
            return ""
            
        # Remove tags HTML
        text = re.sub(r'<.*?>', '', text)
        # Remove URLs
        text = re.sub(r'https?://\S+|www\.\S+', '', text)
        # Remove caracteres especiais
        text = re.sub(r'[^\w\s\.\,\?\!]', '', text)
        # Remove espaços duplicados
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def prepare_for_finetuning(self, include_responses: bool = True) -> int:
        """
        Prepara os dados para fine-tuning no formato:
        {"messages": [{"role": "user", "content": "pergunta"}, {"role": "assistant", "content": "resposta"}]}
        
        Args:
            include_responses: Se deve incluir respostas existentes no treinamento
            
        Returns:
            Número de exemplos de treinamento gerados
        """
        logger.info("Preparando dados para fine-tuning")
        self.training_data = []
        
        if not self.comments_data:
            logger.warning("Nenhum comentário carregado para preparar dados de treinamento")
            return 0
        
        # Agrupar comentários e respostas
        video_comments: Dict[str, List[Dict[str, Any]]] = {}
        
        # Primeiro passo: identificar comentários principais e respostas
        for comment in self.comments_data:
            if not isinstance(comment, dict) or 'video_id' not in comment:
                logger.warning(f"Comentário inválido encontrado: {comment}")
                continue
                
            video_id = comment['video_id']
            
            if 'parent_id' in comment:
                # É uma resposta
                parent_id = comment['parent_id']
                parent_comment = next((c for c in self.comments_data if c.get('comment_id') == parent_id), None)
                
                if parent_comment:
                    if 'responses' not in parent_comment:
                        parent_comment['responses'] = []
                    parent_comment['responses'].append(comment)
            else:
                # É um comentário principal
                if 'comment_id' not in comment:
                    comment['comment_id'] = f"comment_{len(self.training_data)}"
                    
                if video_id not in video_comments:
                    video_comments[video_id] = []
                video_comments[video_id].append(comment)
        
        # Segundo passo: criar exemplos de treino
        examples_count = 0
        for video_id, comments in video_comments.items():
            for comment in comments:
                # Pular comentários sem texto significativo
                if not comment.get('text') or len(comment['text'].split()) < 3:
                    continue
                    
                clean_comment = self.clean_text(comment['text'])
                
                # Se não tem respostas ou não quer incluir respostas, cria exemplo só com o comentário
                if not include_responses or 'responses' not in comment or not comment['responses']:
                    self.training_data.append({
                        "messages": [
                            {"role": "user", "content": clean_comment},
                            {"role": "assistant", "content": "Obrigado pelo seu comentário!"}
                        ]
                    })
                    examples_count += 1
                else:
                    # Para cada resposta, cria um exemplo
                    for response in comment['responses']:
                        if not response.get('text') or len(response['text'].split()) < 2:
                            continue
                            
                        clean_response = self.clean_text(response['text'])
                        self.training_data.append({
                            "messages": [
                                {"role": "user", "content": clean_comment},
                                {"role": "assistant", "content": clean_response}
                            ]
                        })
                        examples_count += 1
        
        logger.info(f"Gerados {examples_count} exemplos de treinamento")
        return len(self.training_data)
    
    def export_training_data(self, filename: str = 'training_data.jsonl') -> str:
        """
        Exporta dados de treinamento no formato JSONL para fine-tuning
        
        Args:
            filename: Nome do arquivo para salvar os dados
            
        Returns:
            Nome do arquivo salvo
        """
        if not self.training_data:
            logger.warning("Nenhum dado de treinamento para exportar")
            return ""
            
        logger.info(f"Exportando {len(self.training_data)} exemplos para {filename}")
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                for item in self.training_data:
                    f.write(json.dumps(item, ensure_ascii=False) + '\n')
            return filename
        except Exception as e:
            logger.error(f"Erro ao exportar dados de treinamento: {str(e)}")
            return ""
    
    def export_to_csv(self, filename: str = 'comments_data.csv') -> str:
        """
        Exporta dados para CSV para análise
        
        Args:
            filename: Nome do arquivo CSV para salvar
            
        Returns:
            Nome do arquivo salvo
        """
        if not self.comments_data:
            logger.warning("Nenhum comentário para exportar para CSV")
            return ""
            
        logger.info(f"Exportando {len(self.comments_data)} comentários para CSV: {filename}")
        
        try:
            df = pd.DataFrame(self.comments_data)
            df.to_csv(filename, index=False, encoding='utf-8')
            return filename
        except Exception as e:
            logger.error(f"Erro ao exportar para CSV: {str(e)}")
            return ""
