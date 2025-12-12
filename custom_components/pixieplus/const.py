"""Constants for the PixiePlus integration."""

DOMAIN = "pixie_plus"

CONF_INSTALLATION_ID = "installation_id"
CONF_SESSION_TOKEN = "session_token"
CONF_USER_OBJECT_ID = "user_object_id"
CONF_CURRENT_HOME_ID = "current_home_id"
CONF_LIVE_GROUP_ID = "live_group_id"
CONF_DEVICES = "devices"

CONF_DEVICE_NAME = "name"
CONF_DEVICE_MAC = "mac"
CONF_DEVICE_ID = "id"
CONF_ONLINE = "online"
CONF_TYPE = "type"
CONF_STYPE = "stype"
CONF_MODEL = "model"
CONF_FIRMWARE = "firmware"
CONF_MANUFACTURER = "manufacturer"
CONF_LIGHT_SWITCH = "light_switch"
CONF_LIGHT_DIMMER = "light_dimmer"
CONF_COVER = "cover"
CONF_RELAY = "relay"
CONF_GPO = "gpo"
CONF_USB = "usb"
CONF_RGB_LIGHT = "rgb_light"
CONF_EFFECTS = "effects"

CMD_ON = "on"
CMD_OFF = "off"
CMD_PLUG_USB_ON = "usb_on"
CMD_PLUG_USB_OFF = "usb_off"
CMD_GPO_ON = "gpo_on"
CMD_GPO_ON_2 = "gpo_on_2"
CMD_GPO_OFF = "gpo_off"
CMD_GPO_OFF_2 = "gpo_off_2"
CMD_RELAY_ON = "relay_on"
CMD_RELAY_OFF = "relay_off"
CMD_RELAY_ON2 = "relay_on2"
CMD_RELAY_OFF2 = "relay_off2"
CMD_SET_COLOR = "set_color"
CMD_SET_BRIGHTNESS = "set_brightness"
CMD_SET_WHITE_BRIGHTNESS = "set_white_brightness"
CMD_SET_EFFECT = "set_effect"
CMD_OPEN = "open"
CMD_CLOSE = "close"
CMD_STOP = "stop"

CMD_PLUG_SWITCH_TYPE = "00c16969"
CMD_LIGHT_SWITCH_TYPE = "00ed6969"
CMD_LIGHT_DIMMER_TYPE = "00c46969ffffff"
CMD_LIGHT_EFFECT_TYPE = "00f86969"

CMD_BLE_DATA_FORMAT = "00-00000304-{{DEST}}-{{CMD_TYPE}}-{{STATE}}-{{CMD_ID}}"


## Example device type stype mapping attributes with default:
# "model" : "<Pixie Model Name",
# "manufacturer": "SAL",
# "light_switch": False,
# "light_dimmer": False,
# "cover": False,
# "relay": 0,
# "gpo": 0,
# "usb": 0,
# "rgb_light": False,
# "effects": []
PIXIE_DEVICES_SPECS = {
    1: {
        2: {
            "model": "Gateway G3 - SGW3BTAM",
            "manufacturer": "SAL",
            "light_switch": False,
            "light_dimmer": False,
            "cover": False,
            "relay": 0,
            "gpo": 0,
            "usb": 0,
            "rgb_light": False,
            "effects": [],
            "command_ids": {},
        },
        7: {
            "model": "Smart plug - ESS105/BT",
            "manufacturer": "SAL",
            "light_switch": False,
            "light_dimmer": False,
            "cover": False,
            "relay": 0,
            "gpo": 1,
            "usb": 1,
            "rgb_light": False,
            "effects": [],
            "command_ids": {
                CMD_ON: "03",
                CMD_OFF: "02",
                CMD_PLUG_USB_ON: "0c",
                CMD_PLUG_USB_OFF: "88",
            },
        },
    },
    2: {
        8: {
            "model": "Smart Socket Outlet - SP023/BTAM",
            "manufacturer": "SAL",
            "light_switch": False,
            "light_dimmer": False,
            "cover": False,
            "relay": 0,
            "gpo": 2,
            "usb": 0,
            "rgb_light": False,
            "effects": [],
            "command_ids": {
                CMD_GPO_ON: "11",
                CMD_GPO_OFF: "10",
                CMD_GPO_ON_2: "21",
                CMD_GPO_OFF_2: "20",
            },
        },
    },
    10: {
        2: {
            "model": "Dual Relay Control - PC206DR/R/BTAM",
            "manufacturer": "SAL",
            "light_switch": False,
            "light_dimmer": False,
            "cover": False,
            "relay": 2,
            "gpo": 0,
            "usbt": 0,
            "rgb_light": False,
            "effects": [],
            "command_ids": {
                CMD_RELAY_ON: "11",
                CMD_RELAY_OFF: "10",
                CMD_RELAY_ON2: "21",
                CMD_RELAY_OFF2: "20",
            },
        },
    },
    11: {
        2: {
            "model": "Blind & Signal Control - PC206BS/R/BTAM",
            "manufacturer": "SAL",
            "light_switch": False,
            "light_dimmer": False,
            "cover": True,
            "relay": 0,
            "gpo": 0,
            "usb": 0,
            "rgb_light": False,
            "effects": [],
            "command_ids": {
                CMD_OPEN: "01",
                CMD_CLOSE: "00",
                CMD_STOP: "02",
            },
        },
    },
    20: {
        13: {
            "model": "rippleSHIELD DIMMER - SDD400SFI",
            "manufacturer": "SAL",
            "light_switch": True,
            "light_dimmer": True,
            "cover": False,
            "relay": 0,
            "gpo": 0,
            "usb": 0,
            "rgb_light": False,
            "effects": [],
            "command_ids": {
                CMD_ON: "01",
                CMD_OFF: "00",
                CMD_SET_BRIGHTNESS: "00",  # value to be set dynamically
            },
        },
    },
    22: {
        12: {
            "model": "Smart Switch G2 - SWL350BT",
            "manufacturer": "SAL",
            "light_switch": True,
            "light_dimmer": False,
            "cover": 0,
            "relay": 0,
            "gpo": 0,
            "usb": 0,
            "rgb_light": False,
            "effects": [],
            "command_ids": {
                CMD_ON: "01",
                CMD_OFF: "00",
            },
        },
        13: {
            "model": "Smart Switch G3 - SWL600BTAM",
            "manufacturer": "SAL",
            "light_switch": True,
            "light_dimmer": False,
            "cover": False,
            "relay": 0,
            "gpo": 0,
            "usb": 0,
            "rgb_light": False,
            "effects": [],
            "command_ids": {
                CMD_ON: "01",
                CMD_OFF: "00",
            },
        },
    },
    23: {
        11: {
            "model": "Smart Dimmer G2 - SDD350BT",
            "manufacturer": "SAL",
            "light_switch": True,
            "light_dimmer": True,
            "cover": False,
            "relay": 0,
            "gpo": 0,
            "usb": 0,
            "rgb_light": False,
            "effects": [],
            "command_ids": {
                CMD_ON: "01",
                CMD_OFF: "00",
                CMD_SET_BRIGHTNESS: "00",  # value to be set dynamically
            },
        },
        12: {
            "model": "Smart Dimmer G2 - SDD350BT",
            "manufacturer": "SAL",
            "light_switch": True,
            "light_dimmer": True,
            "cover": False,
            "relay": 0,
            "gpo": 0,
            "usb": 0,
            "rgb_light": False,
            "effects": [],
            "command_ids": {
                CMD_ON: "01",
                CMD_OFF: "00",
                CMD_SET_BRIGHTNESS: "00",  # value to be set dynamically
            },
        },
        13: {
            "model": "Smart Dimmer G3 - SDD300BTAM",
            "manufacturer": "SAL",
            "light_switch": True,
            "light_dimmer": True,
            "cover": False,
            "relay": 0,
            "gpo": 0,
            "usb": 0,
            "rgb_light": False,
            "effects": [],
            "command_ids": {
                CMD_ON: "01",
                CMD_OFF: "00",
                CMD_SET_BRIGHTNESS: "00",  # value to be set dynamically
            },
        },
    },
    24: {
        2: {
            "model": "Flexi Streamline - FLP24V2M",
            "manufacturer": "SAL",
            "light_switch": True,
            "light_dimmer": True,
            "cover": False,
            "relay": 0,
            "gpo": 0,
            "usb": 0,
            "rgb_light": False,
            "effects": [],
            "command_ids": {
                CMD_ON: "01",
                CMD_OFF: "00",
                CMD_SET_BRIGHTNESS: "00",  # value to be set dynamically
            },
        },
        3: {
            "model": "LED Strip Controller - LT8915DIM/BT",
            "manufacturer": "SAL",
            "light_switch": True,
            "light_dimmer": True,
            "cover": False,
            "relay": 0,
            "gpo": 0,
            "usb": 0,
            "rgb_light": False,
            "effects": [],
            "command_ids": {
                CMD_ON: "01",
                CMD_OFF: "00",
                CMD_SET_BRIGHTNESS: "00",  # value to be set dynamically
            },
        },
    },
    27: {
        2: {
            "model": "Flexi smart LED strip - FLP12V2M/RGBBT",
            "manufacturer": "SAL",
            "light_switch": True,
            "light_dimmer": True,
            "cover": False,
            "relay": 0,
            "gpo": 0,
            "usb": 0,
            "rgb_light": True,
            "effects": ["flash", "strobe", "fade", "smooth"],
            "command_ids": {
                CMD_ON: "01",
                CMD_OFF: "00",
                CMD_SET_COLOR: "00",  # value to be set dynamically
                CMD_SET_BRIGHTNESS: "00",  # value to be set dynamically
                CMD_SET_EFFECT: "00",  # value to be set dynamically
            },
        },
    },
}
