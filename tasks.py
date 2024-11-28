# tasks.py
from asyncio import sleep
from datetime import datetime
from sre_constants import error

from celery import Celery
import pandas as pd
import time
import os

from glpi_client.interface import GLPIApiClient

redis_host = os.getenv('REDIS_HOST')
redis_port = os.getenv('REDIS_PORT')
app = Celery(
    'tasks',
    broker=f'redis://{redis_host}:{redis_port}/0',
    backend=f'redis://{redis_host}:{redis_port}/0'
)


@app.task(bind=True)
def process_csv(self, file_path):
    required = [
        'ticket_name',
        'ticket_content',
        'task_content',
        'ticket_actors_users', # Para a adição dos usuários no ticket
        'ticket_actors_groups', # Para adição dos grupos no ticket
        'Resultado'
    ]
    error_signal = False
    error_list = []
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
        print('--- row ---')
        print(row)
        print('-----------')
        # continue

        self.update_state(state='PROGRESS', meta={'current': index + 1, 'total': total_rows})
        try:
            print('trying')
            enable_ticket_add_users = 'ticket_actors_users' in df.columns
            enable_ticket_add_groups = 'ticket_actors_groups' in df.columns
            ticket_extra_args = task_extra_args = {}
            ticket_extra_columns = [col for col in df.columns if col not in required and col.find('ticket_') != -1]
            task_extra_columns = [col for col in df.columns if col not in required and col.find('task_') != -1]

            if ticket_extra_columns:
                print('ticket_extra_columns')
                ticket_extra_args = { col.replace('ticket_', ''): row[col] for col in ticket_extra_columns }
                print(ticket_extra_args)
            if task_extra_columns:
                print('task_extra_columns')
                task_extra_args = { col.replace('task_', ''): row[col] for col in task_extra_columns}
                print(task_extra_args)


            row['created_ticket_id'] = ticket_id = glpi_client.add_tiket(
                name=row['ticket_name'],
                content=row['ticket_content'],
                **ticket_extra_args
            )
            if enable_ticket_add_users:
                row['ticket_actors_users_response'] = glpi_client.add_ticket_user_actors(
                    tickets_id=ticket_id,
                    actors_users=row['ticket_actors_users']
                )
            if enable_ticket_add_groups:
                row['ticket_actors_groups_response'] = glpi_client.add_ticket_group_actors(
                    tickets_id=row['created_ticket_id'],
                    actors_groups=row['ticket_actors_groups']
                )
            if enable_ticket_add_groups or enable_ticket_add_users:
                time.sleep(10)
                row['ticket_update_status_response'] = glpi_client.update_ticket_status(
                    tickets_id=row['created_ticket_id'],
                    status_id=row['ticket_status']
                )
            if str(ticket_extra_args.get('status')) != '6':
                row['created_task_id'] = glpi_client.add_task_on_ticket(
                    tickets_id=row['created_ticket_id'],
                    content=row['task_content'],
                    **task_extra_args
                )
            row['Resultado'] = "OK"
        except Exception as e:
            error_signal = True
            error_list.append(str(e))
            row['Resultado'] = f'FALHA: {e}'


        # Exemplo de processamento (substitua pela sua lógica)
        processed_row = row  # Implementar a lógica de processamento aqui
        result_data.append(processed_row)

    # Salvar resultado em um novo arquivo CSV
    result_df = pd.DataFrame(result_data)
    result_csv_path = os.getenv('PROCESSED_FOLDER') + '/' + self.request.id + '_processed.csv'
    # result_csv_path = file_path.replace('.csv', '_processed.csv').replace('temp_files', os.getenv('PROCESSED_FOLDER'))

    result_df.to_csv(result_csv_path, index=False)
    if error_signal:
        return {'status': 'completed_with_fail','result_csv': result_csv_path, 'error': error_list}
    return {'status': 'completed', 'result_csv': result_csv_path}
