import streamlit as st
from streamlit_autorefresh import st_autorefresh


def set_auto_refresh(timeout=60000, st_app=None, auto_refresh=True):
    global count
    count = None
    st_app.session_state.auto_refresh = auto_refresh
    count = st_autorefresh(interval=timeout, limit=1000, key="fizzbuzzcounter")


def set_auto_refresh_controller(st_app):
    if 'auto_refresh' not in st_app.session_state:
        st_app.session_state.auto_refresh = True

    if st_app.session_state.auto_refresh:
        st_app.button(
            'Desabilitar auto-regfresh',
            on_click=set_auto_refresh,
            kwargs={
                'st_app': st_app,
                'auto_refresh': False
            },
            type='secondary'
        )
    else:
        st_app.button(
            'Habilitar auto-refresh',
            on_click=set_auto_refresh,
            kwargs = {
                'timeout': 2000,
                'st_app': st_app
            },
            type='primary'
        )