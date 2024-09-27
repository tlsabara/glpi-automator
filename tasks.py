# tasks.py
from asyncio import sleep
from datetime import datetime

from celery import Celery
import pandas as pd
import time
import os

from glpi_client.interface import GLPIApiClient

# Configurar o Celery com Redis como broker e backend
app = Celery('tasks', broker='redis://redis:6379/0', backend='redis://redis:6379/0')


@app.task(bind=True)
def process_csv(self, file_path):
    try:
        glpi_client = GLPIApiClient(
            username='glpi',
            password='glpi',
        )
        df = pd.read_csv(file_path, sep=';', encoding='utf-8', )
    except Exception as e:
        self.update_state(state='FAILURE', meta={'error': str(e)})
        print(e)
        return {'status': 'failed', 'error': str(e)}

    total_rows = len(df)
    result_data = []
    df['Resultado'] = 'WAIT'

    for index, row in df.iterrows():
        print(row)
        self.update_state(state='PROGRESS', meta={'current': index + 1, 'total': total_rows})
        try:
            row['created_ticket_id'] = glpi_client.add_tiket(
                name=row['ticket_name'] + datetime.now().strftime('%Y%m%d%H%M%S'),
                content=row['ticket_content'] + datetime.now().strftime('%Y%m%d%H%M%S')
            )
            sleep(2)
            print(row['created_ticket_id'])
            row['created_task_id'] = glpi_client.add_task_on_ticket(
                tickets_id=row['created_ticket_id'],
                content=row['task_content'] + datetime.now().strftime('%Y%m%d%H%M%S')
            )
            row['Resultado'] = "OK"
        except Exception as e:
            raise e
            self.update_state(state='FAILURE', meta={'error': str(e)})
            row['Resultado'] = 'FALHA'
            return {'status': 'failed', 'error': str(e)}

        # Exemplo de processamento (substitua pela sua lógica)
        processed_row = row  # Implementar a lógica de processamento aqui
        result_data.append(processed_row)

    # Salvar resultado em um novo arquivo CSV
    result_df = pd.DataFrame(result_data)
    result_csv_path = file_path.replace('.csv', '_processed.csv')
    result_df.to_csv(result_csv_path, index=False)

    return {'status': 'completed', 'result_csv': result_csv_path}
