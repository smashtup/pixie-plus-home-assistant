"""Pixie Plus Cloud API"""

import websocket
import json
import uuid
import logging

from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from .const import (
    CONF_INSTALLATION_ID,
    CONF_SESSION_TOKEN,
    CONF_USER_OBJECT_ID,
    CONF_CURRENT_HOME_ID,
    CONF_LIVE_GROUP_ID,
)

PIXIE_PLUS_CLOUD_URL = "https://www.pixie.app/p0/pixieCloud/"
PIXIE_PLUS_CLOUD_WS_URL = "wss://www.pixie.app/ws/p0/pixieCloud"
PIXIE_PLUS_CLOUD_APPLICATION_ID = "6426f04c206c108275ede71b9fd09ac8"
PIXIE_PLUS_CLOUD_CLIENT_KEY = "35779bd411c751ff87577cd762118dad"

_LOGGER = logging.getLogger(__name__)


class PixiePlusCloud:
    def __init__(
        self,
        httpx_client,
        username: str,
        password: str,
        installation_id: str = "",
        user_object_id: str = "",
        session_token: str = "",
        current_home_id: str = "",
        live_group_id: str = "",
    ):
        self._httpx_client = httpx_client
        self._username = username
        self._password = password
        self._installation_id = installation_id
        self._user_object_id = user_object_id
        self._session_token = session_token
        self._current_home_id = current_home_id
        self._live_group_id = live_group_id

        self._pixieplus_ws_conn = None
        self._pixieplus_ws_listeners = {}
        self._pixieplus_ws_connected = False
        self._pixieplus_ws_client_id = ""

        if not self._installation_id:
            self._installation_id = str(uuid.uuid4())

    async def login(self):
        payload = json.dumps(
            {"username": self._username, "password": self._password, "_method": "GET"}
        )

        headers = {
            "x-parse-application-id": PIXIE_PLUS_CLOUD_APPLICATION_ID,
            "x-parse-installation-id": self._installation_id,
            "x-parse-client-key": PIXIE_PLUS_CLOUD_CLIENT_KEY,
            "content-type": "application/json",
        }

        response = await self._httpx_client.request(
            "POST", PIXIE_PLUS_CLOUD_URL + "login", headers=headers, data=payload
        )

        if response.status_code != 200:
            raise Exception("Login failed - %s" % response.json()["error"])

        self._user_object_id = response.json()["objectId"]
        self._session_token = response.json()["sessionToken"]
        self._current_home_id = (
            response.json()["curHome"]["objectId"]
            if "curHome" in response.json()
            else self._current_home_id
        )

    def connect_ws(self, ssl_context):
        websocket.enableTrace(True)

        self._pixieplus_ws_conn = websocket.WebSocketApp(
            PIXIE_PLUS_CLOUD_WS_URL,
            header={},
            on_open=self._on_ws_open,
            on_message=self._on_ws_message,
            on_error=self._on_ws_error,
            on_close=self._on_ws_close,
        )
        return self._pixieplus_ws_conn.run_forever(
            sslopt={"context": ssl_context}, reconnect=5
        )

    def close_ws(self):
        if self._pixieplus_ws_conn is not None:
            self._pixieplus_ws_connected = False
            self._pixieplus_ws_conn.close()

    def _on_ws_open(self, ws):
        _LOGGER.info("Opened connection to PixiePlus WebSocket endpoint")
        payload = json.dumps(
            {
                "op": "connect",
                "applicationId": PIXIE_PLUS_CLOUD_APPLICATION_ID,
                "sessionToken": self._session_token,
                "clientKey": PIXIE_PLUS_CLOUD_CLIENT_KEY,
            }
        )
        ws.send(payload)

    def _on_ws_message(self, ws, message: str):
        message_data = json.loads(message)
        opcode = message_data.get("op", None)
        clientId = message_data.get("clientId", "")
        classObject = message_data.get("object", None)

        if opcode == "connected" and clientId is not None:
            _LOGGER.info("Connected to PixiePlus Cloud WebSocket")
            self._pixieplus_ws_client_id = clientId
            self._subscribeHomeUpdates(ws)
            self._subscribeLiveGroupUpdates(ws)
            self._subscribeHPUpdates(ws)
            return
        if opcode == "subscribed" and clientId == self._pixieplus_ws_client_id:
            _LOGGER.info(
                "Subscribed to PixiePlus Cloud Class Updates: %s", message_data
            )
            return
        if opcode == "update":
            _LOGGER.info("Received update message: %s", message_data)
            if classObject is not None:
                className = classObject.get("className", None)
                if (
                    className is not None
                    and self._pixieplus_ws_client_id
                    == message_data.get("clientId", None)
                ):
                    if className in self._pixieplus_ws_listeners:
                        for callback in self._pixieplus_ws_listeners[className]:
                            callback(classObject)
            return

        _LOGGER.info("Received message with unknown opcode %s", message)

    def _on_ws_error(self, ws, error: str):
        _LOGGER.error("WebSocket error: %s", error)

    def _on_ws_close(self, ws, close_status_code: int, close_msg: str):
        _LOGGER.info("WebSocket closed: %s - %s", close_status_code, close_msg)

    def _ws_subscribe_class(
        self, ws, request_id, class_name: str, where_value: dict = {}
    ):
        payload = json.dumps(
            {
                "op": "subscribe",
                "query": {"className": class_name, "where": where_value},
                "requestId": request_id,
                "sessionToken": self._session_token,
            }
        )
        ws.send(payload)

    def _subscribe_class_update_listener(self, class_name: str, callback: any):
        if class_name not in self._pixieplus_ws_listeners:
            self._pixieplus_ws_listeners[class_name] = []
        self._pixieplus_ws_listeners[class_name].append(callback)

    def _subscribeHomeUpdates(self, ws):
        self._ws_subscribe_class(ws, 2, "Home", {"objectId": self._current_home_id})

    def _subscribeLiveGroupUpdates(self, ws):
        self._ws_subscribe_class(ws, 1, "LiveGroup", {"objectId": self._live_group_id})

    def _subscribeHPUpdates(self, ws):
        self._ws_subscribe_class(
            ws,
            3,
            "HP",
            {"homeId": self._current_home_id, "userId": self._user_object_id},
        )

    async def _fetch_class(
        self, class_name: str, where: dict = {"where": {}, "_method": "GET"}
    ):
        payload = json.dumps(where)
        headers = {
            "x-parse-application-id": PIXIE_PLUS_CLOUD_APPLICATION_ID,
            "x-parse-installation-id": self._installation_id,
            "x-parse-client-key": PIXIE_PLUS_CLOUD_CLIENT_KEY,
            "content-type": "application/json",
            "x-parse-session-token": self._session_token,
        }

        response = await self._httpx_client.request(
            "POST",
            PIXIE_PLUS_CLOUD_URL + "classes/" + class_name,
            headers=headers,
            data=payload,
        )

        if response.status_code != 200:
            raise Exception("Loading data failed - %s" % response.json()["error"])

        return response.json()["results"]

    async def userObjectId(self):
        if self._user_object_id is None or self._user_object_id == "":
            results = await self._fetch_class(
                "_User", {"where": {"username": self._username}, "_method": "GET"}
            )
            self._user_object_id = results[0]["objectId"]
        return self._user_object_id

    async def currentHomeId(self):
        if self._current_home_id is None or self._current_home_id == "":
            results = await self._fetch_class("Home")
            self._current_home_id = results[0]["objectId"]
        return self._current_home_id

    async def liveGroupId(self):
        if self._live_group_id is not None or self._live_group_id == "":
            return self._live_group_id

        results = await self._fetch_class(
            "LiveGroup",
            {
                "where": {
                    "GroupID": {
                        "$regex": await self.currentHomeId() + "$",
                        "$options": "i",
                    }
                },
                "limit": 2,
                "_method": "GET",
            },
        )

        return results[0]["objectId"]

    async def devices(self):
        results = await self._fetch_class("Home")
        return results[0]["deviceList"]

    async def credentials(self):
        return {
            CONF_USERNAME: self._username,
            CONF_PASSWORD: self._password,
            CONF_INSTALLATION_ID: self._installation_id,
            CONF_SESSION_TOKEN: self._session_token,
            CONF_USER_OBJECT_ID: await self.userObjectId(),
            CONF_CURRENT_HOME_ID: await self.currentHomeId(),
            CONF_LIVE_GROUP_ID: await self.liveGroupId(),
        }
