import base64
import json
import os
from datetime import datetime
from typing import Tuple, Any

from dotenv import load_dotenv
import httpx

from .error import InitSessionError, ClientGlpiError401, ClientGlpiError400


class BasicAuth:
    def __init__(self, username: str, password: str) -> None:
        self.username = username
        self.password = password

    @property
    def auth(self) -> str:
        return httpx.BasicAuth(username=self.username, password=self.password)

class GLPIApiClient:
    def __init__(self, username: str, password: str) -> None:
        load_dotenv()
        self.__api_server_endpoint: str = os.getenv('GLPI_API_ENDPOINT', 'http://localhost:8090/apirest.php')
        self.__app_token: str = os.getenv('GLPI_APP_TOKEN', 'no_token_found')
        self.__basic_auth: BasicAuth = BasicAuth(username=username, password=password)
        self.__session_token: str = ''
        self._api_client = httpx.Client(auth=self.__basic_auth.auth)

        self._init_session()

    @property
    def auth_headers(self) -> httpx.Headers:
        headers =  {
            'App-Token': self.__app_token,
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Content-Type': 'application/json',
            'Connection': 'keep-alive',
        }
        if self.__session_token:
            headers['Session-Token'] = self.__session_token

        header_request = httpx.Headers(headers, 'UTF-8')
        print(header_request)
        return header_request

    def _init_session(self) -> None:
        endpoint = self.__api_server_endpoint + '/initSession'
        response = self._api_client.post(endpoint, headers=self.auth_headers)
        print(response.text)
        if response.status_code == 200:
            self.__session_token = response.json()['session_token']
        else:
            raise InitSessionError()

    def __request_add_ticket(self, name: str, content:str, **kwargs) -> tuple[Any, Any] | tuple[Any, None]:
        endpoint = self.__api_server_endpoint + '/Ticket'
        body_data = {
            'input': {
                'name': name,
                'content': content,
                **kwargs
            }
        }
        response = self._api_client.post(endpoint, headers=self.auth_headers, json=body_data)
        if response.status_code == 201:
            return response.status_code, response.json()['id']
        else:
            return response.status_code, None

    def add_tiket(self, name: str, content:str, **kwargs) -> str:
        data = self.__request_add_ticket(name, content, **kwargs)
        if data[0] == 201:
            return data[1]
        else:
            return self.__request_error_handler(data[0], 'unhandled error on add ticket')

    def __request_error_handler(self, status_code: int, message:str):
        if status_code == 401:
            self._init_session()
            raise ClientGlpiError401()
        elif status_code == 400:
            #! TODO: tratamento de erro para APP_TOKEN inválido
            raise ClientGlpiError400()
        else:
            return message

    def __request_add_task_on_ticket(self, tickets_id: str, content: str, state: int = 1, **kwargs) -> tuple[Any, Any] | tuple[Any, None]:
        endpoint = self.__api_server_endpoint + '/TicketTask'
        body_data = {
            'input': {
                'tickets_id': tickets_id,
                'content': content,
                'state': state,
                **kwargs
            }
        }
        print(json.dumps(body_data))
        response = self._api_client.post(endpoint, headers=self.auth_headers, json=body_data)
        print(response.text)
        if response.status_code == 201:
            return response.status_code, response.json()['id']
        return response.status_code, None

    def add_task_on_ticket(self, tickets_id: str, content: str, state: int = 1, **kwargs) -> str:
        data = self.__request_add_task_on_ticket(tickets_id=tickets_id, content=content, state=state, **kwargs)
        if data[0] == 201:
            return data[1]
        else:
            return self.__request_error_handler(data[0], 'unhandled error on add ticket')