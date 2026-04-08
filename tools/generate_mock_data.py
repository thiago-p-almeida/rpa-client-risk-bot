# tools/generate_mock_data.py
import pandas as pd
import os
import time

def generate_excel_batch(num_records=500):
    """Gera uma planilha Excel com dados fictícios e IDs únicos para teste de carga."""
    
    input_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'input'))
    os.makedirs(input_dir, exist_ok=True)
    
    # Cria um prefixo único baseado no relógio do computador (Timestamp)
    # Exemplo: 1712590000
    batch_id = int(time.time()) 
    
    data = {
        # Gera IDs no formato: C-1712590000-001
        'client_id':[f'C-{batch_id}-{str(i).zfill(3)}' for i in range(num_records)],
        'name':[f'Cliente Teste {batch_id}-{i}' for i in range(num_records)],
        'email':[f'cliente{i}_{batch_id}@empresa.com' for i in range(num_records)]
    }
    
    df = pd.DataFrame(data)
    
    file_path = os.path.join(input_dir, f'lote_{batch_id}.xlsx')
    df.to_excel(file_path, index=False, engine='openpyxl')
    
    print(f"✅ Arquivo gerado com sucesso: {file_path}")
    print(f"📊 Total de registros: {num_records}")

if __name__ == "__main__":
    generate_excel_batch()