"""Pixie Plus Cloud API"""
import requests
import websocket
import json
import uuid
import logging

from homeassistant.const import (
    CONF_USERNAME,
    CONF_PASSWORD
)
from .const import (
    CONF_INSTALLATION_ID,
    CONF_SESSION_TOKEN,
    CONF_USER_OBJECT_ID,
    CONF_CURRENT_HOME_ID,
    CONF_LIVE_GROUP_ID)

PIXIE_PLUS_CLOUD_URL = 'https://www.pixie.app/p0/pixieCloud/'
PIXIE_PLUS_CLOUD_WS_URL = 'wss://ws.pixie.app/websocket'
PIXIE_PLUS_CLOUD_APPLICATION_ID = '6426f04c206c108275ede71b9fd09ac8'
PIXIE_PLUS_CLOUD_CLIENT_KEY = '35779bd411c751ff87577cd762118dad'

_LOGGER = logging.getLogger(__name__)

class PixiePlusCloud:

    def __init__(self, 
                 username: str, 
                 password: str, 
                 installation_id: str = None,
                 user_object_id: str = None,
                 session_token: str = None, 
                 current_home_id: str = None,
                 live_group_id: str = None):
        
        self._username = username
        self._password = password
        self._installation_id = installation_id
        self._user_object_id = user_object_id
        self._session_token = session_token
        self._cur_home_id = current_home_id
        self._live_group_id = live_group_id

        self._pixieplus_ws_conn = None
        self._pixieplus_ws_listeners = {}
        self._pixieplus_ws_connected = False

        if not self._installation_id:
            self._installation_id = str(uuid.uuid4())

    async def login(self):
        payload = json.dumps({"username": self._username, "password": self._password, "_method": "GET"})

        headers = {
            'x-parse-application-id': PIXIE_PLUS_CLOUD_APPLICATION_ID,
            'x-parse-installation-id': self._installation_id,
            'x-parse-client-key': PIXIE_PLUS_CLOUD_CLIENT_KEY,
            'content-type': 'application/json'
        }

        response = requests.request("POST", PIXIE_PLUS_CLOUD_URL + 'login', headers=headers, data=payload)

        if response.status_code != 200:
            raise Exception('Login failed - %s' % response.json()['error'])

        self._user_object_id = response.json()['objectId']
        self._session_token = response.json()['sessionToken']
        self._cur_home_id = response.json()['curHome']['objectId'] if 'curHome' in response.json() else None
    
    async def connect_ws(self):
        self._pixieplus_ws_conn = websocket.WebSocketApp(PIXIE_PLUS_CLOUD_WS_URL,
                                    header={},
                                    on_open=self._on_ws_open,
                                    on_message=self._on_ws_message,
                                    on_error=self._on_ws_error,
                                    on_close=self._on_ws_close)
        self._pixieplus_ws_conn.run_forever()
    
    def _on_ws_open(self):
        _LOGGER.info("Opened connection to PixiePlus WebSocket endpoint")
        payload = json.dumps({
            "op": "connect",
            "applicationId": PIXIE_PLUS_CLOUD_APPLICATION_ID,
            "sessionToken": self._session_token,
            "clientKey": PIXIE_PLUS_CLOUD_CLIENT_KEY
        })
        self._pixieplus_ws_conn.send(payload);

    def _on_ws_message(self, message: str):
        message_data = json.loads(message)
        opcode = message_data.get('op', None)
        clientId = message_data.get('clientId', None)
        classObject = message_data.get('object', None)

        if opcode == 'connected' and clientId is not None:
            _LOGGER.info("Connected to PixiePlus Cloud WebSocket")
            self._pixieplus_ws_client_id = clientId
            return            
        if opcode == 'subscribed' and clientId == self._pixieplus_ws_client_id:
            _LOGGER.info("Subscribed to PixiePlus Cloud Class Updates: %s", message_data)
            return
        if opcode == 'update':
            _LOGGER.debug("Received update message: %s", message_data)
            if classObject is not None:
                className = classObject.get('className', None)
                if className is not None and self._pixieplus_ws_client_id == message_data.get('clientId', None):
                    if className in self._pixieplus_ws_listeners:
                        for callback in self._pixieplus_ws_listeners[className]:
                            callback(classObject)
            return

    def _on_ws_error(self, error: str):
        _LOGGER.error("WebSocket error: %s", error)

    def _on_ws_close(self, close_status_code: int, close_msg: str):
        _LOGGER.info("WebSocket closed: %s - %s", close_status_code, close_msg)

    def _ws_subscribe_class(self, class_name: str, where: any = {"where": {}}, callback: any = None):
        payload = json.dumps({
            "op": "subscribe",
            "requestId": "1",
            "query": {
                "className": class_name,
                "where": where['where']
            }
        })

    def _subscribe_class_update_listener(self, class_name: str, callback: any):
        if class_name not in self._pixieplus_ws_listeners:
            self._pixieplus_ws_listeners[class_name] = []
        self._pixieplus_ws_listeners[class_name].append(callback)

    async def _fetch_class(self, class_name: str, where: any = {"where": {}, "_method": "GET"}):
        payload = json.dumps(where)
        headers = {
            'x-parse-application-id': PIXIE_PLUS_CLOUD_APPLICATION_ID,
            'x-parse-installation-id': self._installation_id,
            'x-parse-client-key': PIXIE_PLUS_CLOUD_CLIENT_KEY,
            'content-type': 'application/json',
            'x-parse-session-token': self._session_token
        }

        response = requests.request("POST", self.api_url + 'classes/' + class_name, headers=headers, data=payload)

        if response.status_code != 200:
            raise Exception('Loading data failed - %s' % response.json()['error'])

        return response.json()['results']

    async def userObjectId(self):
        if (self._user_object_id is None):
            self._user_object_id = self._fetch_class('_User', {"where": {"username": self._username},"_method": "GET",})[0]['objectId']
        return self._user_object_id

    async def currentHomeId(self):
        if self._cur_home_id is None:
            self._cur_home_id = self._fetch_class('Home')[0]['objectId']
        return self._cur_home_id

    async def liveGroupId(self):
        if self._live_group_id is not None:
            return self._live_group_id
        else:
            return self._fetch_class('LiveGroup', {"where": {"GroupID": {"$regex": self.currentHomeId(self) + "$", "$options": "i"}},"limit": 2,})[0]['objectId']

    async def devices(self):
        return self._fetch_class('Home')[0]['deviceList']

    async def credentials(self):
        credentials = {
            CONF_USERNAME: self._username,
            CONF_PASSWORD: self._password,
            CONF_INSTALLATION_ID:  self._installation_id,
            CONF_SESSION_TOKEN: self._session_token,
            CONF_USER_OBJECT_ID: self.userObjectId(self),
            CONF_CURRENT_HOME_ID: self.currentHomeId(self),
            CONF_LIVE_GROUP_ID: self.liveGroupId(self)
        }
        return credentials
