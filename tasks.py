# tasks.py
from celery import Celery
import pandas as pd
import time
import os

# Configurar o Celery com Redis como broker e backend
app = Celery('tasks', broker='redis://redis:6379/0', backend='redis://redis:6379/0')


@app.task(bind=True)
def process_csv(self, file_path):
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        self.update_state(state='FAILURE', meta={'error': str(e)})
        return {'status': 'failed', 'error': str(e)}

    total_rows = len(df)
    result_data = []

    for index, row in df.iterrows():
        # Simular tempo de processamento
        time.sleep(5)

        # Atualizar estado da tarefa
        self.update_state(state='PROGRESS', meta={'current': index + 1, 'total': total_rows})

        # Exemplo de processamento (substitua pela sua lógica)
        processed_row = row  # Implementar a lógica de processamento aqui
        result_data.append(processed_row)

    # Salvar resultado em um novo arquivo CSV
    result_df = pd.DataFrame(result_data)
    result_csv_path = file_path.replace('.csv', '_processed.csv')
    result_df.to_csv(result_csv_path, index=False)

    return {'status': 'completed', 'result_csv': result_csv_path}
