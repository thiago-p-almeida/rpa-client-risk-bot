import psycopg2
import sys
import os
from datetime import datetime

# Adiciona a pasta raiz ao sys.path para conseguir importar o config da API
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from api.config import DB_CONFIG

def populate_initial_clients():
    """Insere clientes de teste no banco de dados."""
    clients_to_add = [
        ("C-001", "Ana Silva", "ana@email.com"),
        ("C-002", "Bruno Costa", "bruno@email.com"),
        ("C-003", "Carla Souza", "carla@email.com")
    ]

    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        insert_query = """
            INSERT INTO clients (client_id, name, email)
            VALUES (%s, %s, %s)
            ON CONFLICT (client_id) DO NOTHING;
        """

        for client in clients_to_add:
            cur.execute(insert_query, client)
        
        conn.commit()
        print(f"✅ {len(clients_to_add)} clientes processados com sucesso no banco!")

    except Exception as e:
        print(f"❌ Erro na ingestão: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            if cur: cur.close()
            conn.close()

if __name__ == "__main__":
    populate_initial_clients()
