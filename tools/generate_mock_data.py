# tools/generate_mock_data.py
import pandas as pd
import os

def generate_excel_batch(num_records=500):
    """Gera uma planilha Excel com dados fictícios para teste de carga do RPA."""
    
    # Garante que a pasta de input exista
    input_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'input'))
    os.makedirs(input_dir, exist_ok=True)
    
    # Gera os dados
    data = {
        'client_id':[f'C-{str(i).zfill(4)}' for i in range(100, 100 + num_records)],
        'name':[f'Cliente Teste {i}' for i in range(100, 100 + num_records)],
        'email':[f'cliente{i}@empresa.com' for i in range(100, 100 + num_records)]
    }
    
    df = pd.DataFrame(data)
    
    # Salva o arquivo
    file_path = os.path.join(input_dir, 'lote_clientes_01.xlsx')
    df.to_excel(file_path, index=False, engine='openpyxl')
    
    print(f"✅ Arquivo gerado com sucesso: {file_path}")
    print(f"📊 Total de registros: {num_records}")

if __name__ == "__main__":
    generate_excel_batch()