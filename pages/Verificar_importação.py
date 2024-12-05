# pages/Verificar_importação.py
import streamlit as st
from celery.result import AsyncResult
from celery import Celery
import pandas as pd
import os
from dotenv import load_dotenv
from app_utils.auto_refresh import set_auto_refresh_controller

global count

load_dotenv()
redis_host = os.getenv('REDIS_HOST')
redis_port = os.getenv('REDIS_PORT')
celery_app = Celery(
    'tasks',
    broker=f'redis://{redis_host}:{redis_port}/0',
    backend=f'redis://{redis_host}:{redis_port}/0'
)

def csv_finder(folder, task_id):
    filename = f'{task_id}_processed.csv'
    file = os.path.join(folder, filename)
    if os.path.exists(file):
        return file
    else:
        return None

def main():
    processed_folder = os.getenv('PROCESSED_FOLDER')
    st.title('Verificar Resultado da Tarefa')
    st.text('Com o id da tarefa você pode verificar o andamento do processamento.')

    set_auto_refresh_controller(st)

    task_id_input = st.text_input('Insira o ID da tarefa:', '')

    if st.button('Verificar o resultado da tarefa'):
        if task_id_input:
            task_result = csv_finder(processed_folder, task_id_input)
            st.write(f"**Tarefa ID:** {task_id_input}")

            if not task_result:
                st.info('Tarefa não encontrada, ou não finalizada.')
            else:
                st.success('Processamento da tarefa foi concluído!')
                result_df = pd.read_csv(task_result)
                st.dataframe(result_df)

            # elif task_result.state == 'PROGRESS':
            #     progress = task_result.info
            #     current = progress.get('current', 0)
            #     total = progress.get('total', 1)
            #     percent = int((current / total) * 100)
            #     st.progress(percent / 100.0)
            #     st.write(f'Processando linha {current} de {total}')
            # elif task_result.state == 'SUCCESS':
            #     result = task_result.result
            #     if result['status'] == 'completed':
            #         st.success('Processamento concluído!')
            #         # Exibir botão para ver o resultado
            #         if st.button(f"Ver resultado da tarefa {task_id_input}"):
            #             result_csv_path = result['result_csv']
            #             if os.path.exists(result_csv_path):
            #                 result_df = pd.read_csv(result_csv_path)
            #                 st.dataframe(result_df)
            #             else:
            #                 st.error('O arquivo de resultado não foi encontrado.')
            #     else:
            #         st.error('O processamento falhou.')
            # elif task_result.state == 'FAILURE':
            #     st.error('Ocorreu um erro durante o processamento.')
            # else:
            #     st.write(f'Status da tarefa: {task_result.state}')
        else:
            st.warning('Por favor, insira um ID de tarefa válido.')

if __name__ == '__main__':
    main()
