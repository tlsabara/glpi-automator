# pages/status.py
import streamlit as st
from celery.result import AsyncResult
from celery import Celery
import pandas as pd
from streamlit_autorefresh import st_autorefresh


count = st_autorefresh(interval=2000, limit=1000, key="fizzbuzzcounter")
# Configurar o Celery para se conectar ao backend Redis
celery_app = Celery('tasks', broker='redis://redis:6379/0', backend='redis://redis:6379/0')

def main():
    st.title('Status do Processamento')

    # Recuperar a lista de tarefas do estado da sessão
    if 'task_ids' not in st.session_state or not st.session_state.task_ids:
        st.write("Nenhuma tarefa em andamento.")
        return

    for task_id in st.session_state.task_ids:
        task_result = AsyncResult(task_id, app=celery_app)
        st.write(f"**Tarefa ID:** {task_id}")

        if task_result.state == 'PENDING':
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
                # Exibir botão para ver o resultado
                if st.button(f"Ver resultado da tarefa {task_id}"):
                    result_csv_path = result['result_csv']
                    result_df = pd.read_csv(result_csv_path)
                    st.dataframe(result_df)
            else:
                st.error('O processamento falhou.')
        elif task_result.state == 'FAILURE':
            st.error('Ocorreu um erro durante o processamento.')
        else:
            st.write(f'Status da tarefa: {task_result.state}')

if __name__ == '__main__':
    main()