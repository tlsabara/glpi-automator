# app.py
import streamlit as st
import pandas as pd
import os
import uuid
from celery.result import AsyncResult
from tasks import process_csv
from celery import Celery
from streamlit_autorefresh import st_autorefresh


count = st_autorefresh(interval=2000, limit=1000, key="fizzbuzzcounter")

# Configurar o Celery para se conectar ao backend Redis
celery_app = Celery('tasks', broker='redis://redis:6379/0', backend='redis://redis:6379/0')

def main():
    st.title('Criação de tickets em massa - GLPI')

    # Inicializar o estado da sessão
    if 'task_ids' not in st.session_state:
        st.session_state.task_ids = []

    # Formulário para upload de arquivo
    with st.form(key='upload_form'):
        uploaded_file = st.file_uploader('Escolha um arquivo CSV', type=['csv'])
        submit_button = st.form_submit_button(label='Processar')

    if submit_button:
        if uploaded_file is not None:
            # Salvar o arquivo em uma pasta temporária
            temp_dir = 'temp_files'
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
            file_id = str(uuid.uuid4())
            temp_file_path = os.path.join(temp_dir, f'{file_id}.csv')
            with open(temp_file_path, 'wb') as f:
                f.write(uploaded_file.getbuffer())

            # Enviar tarefa para o Celery
            task = process_csv.delay(temp_file_path)
            st.session_state.task_ids.append(task.id)
            st.success(f'Tarefa {task.id} enviada para processamento!')
        else:
            st.warning('Por favor, faça o upload de um arquivo CSV.')

    st.write("Para ver o status das tarefas, acesse a página 'Status do Processamento' no menu à esquerda.")

if __name__ == '__main__':
    main()
