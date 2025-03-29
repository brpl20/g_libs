#!/bin/bash

# Cria um arquivo temporário para armazenar conteúdos já vistos
temp_file=$(mktemp)

# Processa cada linha do arquivo de entrada
while IFS= read -r line; do
  # Extrai o conteúdo do usuário usando jq
  user_content=$(echo "$line" | jq -r '.messages[0].content')
  
  # Verifica se este conteúdo já foi visto antes
  if ! grep -Fxq "$user_content" "$temp_file"; then
    # Se não foi visto, imprime a linha e adiciona o conteúdo ao arquivo temporário
    echo "$line"
    echo "$user_content" >> "$temp_file"
  fi
done < training_data.jsonl > training_data_clean.json

# Remove o arquivo temporário
rm "$temp_file"