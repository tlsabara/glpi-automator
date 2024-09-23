# pages/check_task.py
import streamlit as st
from celery.result import AsyncResult
from celery import Celery
import pandas as pd

# Configurar o Celery para se conectar ao backend Redis
celery_app = Celery('tasks', broker='redis://redis:6379/0', backend='redis://redis:6379/0')

def main():
    st.title('Verificar Status da Tarefa pelo ID')

    task_id_input = st.text_input('Insira o ID da tarefa:', '')

    if st.button('Verificar Status'):
        if task_id_input:
            task_result = AsyncResult(task_id_input, app=celery_app)
            st.write(f"**Tarefa ID:** {task_id_input}")

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
                    if st.button(f"Ver resultado da tarefa {task_id_input}"):
                        result_csv_path = result['result_csv']
                        if os.path.exists(result_csv_path):
                            result_df = pd.read_csv(result_csv_path)
                            st.dataframe(result_df)
                        else:
                            st.error('O arquivo de resultado não foi encontrado.')
                else:
                    st.error('O processamento falhou.')
            elif task_result.state == 'FAILURE':
                st.error('Ocorreu um erro durante o processamento.')
            else:
                st.write(f'Status da tarefa: {task_result.state}')
        else:
            st.warning('Por favor, insira um ID de tarefa válido.')

if __name__ == '__main__':
    main()
