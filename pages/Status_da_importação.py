# pages/Status_da_importação.py
import streamlit as st
import os
from celery.result import AsyncResult
from celery import Celery
import pandas as pd
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

def main():
    st.title('Status do Processamento')
    set_auto_refresh_controller(st)

    # Recuperar a lista de tarefas do estado da sessão
    if 'task_ids' not in st.session_state or not st.session_state.task_ids:
        st.write("Nenhuma tarefa em andamento.")
        return

    for task_id in st.session_state.task_ids:
        try:
            task_result = AsyncResult(task_id, app=celery_app)
            # task_result.get()
        except Exception as e:
            task_result = None
        st.write(f"**Tarefa ID:** {task_id}")
        if task_result is None:
            st.error('Ocorreu um erro durante o processamento.')
        elif task_result.state == 'PENDING':
            st.info('A tarefa está na fila de processamento.')
        elif task_result.state == 'PROGRESS':
            progress = task_result.info
            current = progress.get('current', 0)
            total = progress.get('total', 1)
            percent = int((current / total) * 100)
            st.progress(percent / 100.0)
            st.write(f'Processando linha {current} de {total}')
        elif task_result.state == 'SUCCESS':
            result = task_result.result
            if result['status'] == 'completed':
                st.success('Processamento concluído!')
                if st.button(f"Ver resultado da tarefa {task_id}"):
                    result_csv_path = result['result_csv']
                    result_df = pd.read_csv(result_csv_path)
                    st.dataframe(result_df)
            else:
                st.error('O processamento falhou.')
        else:
            st.write(f'Status da tarefa: {task_result.state}')

if __name__ == '__main__':
    main()
