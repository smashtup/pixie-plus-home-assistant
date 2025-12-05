from os import urandom
import struct

from .const import (
    PIXIE_DEVICES_SPECS,
    CMD_ON,
    CMD_OFF, 
    CMD_SET_COLOR,
    CMD_SET_BRIGHTNESS,
    CMD_SET_WHITE_BRIGHTNESS,
    CMD_SET_EFFECT,
    CMD_PLUG_USB_ON,
    CMD_PLUG_USB_OFF,
    CMD_GPO_ON,
    CMD_GPO_ON_2,
    CMD_GPO_OFF,
    CMD_GPO_OFF_2,
    CMD_RELAY_ON,
    CMD_RELAY_OFF,
    CMD_RELAY_ON2,
    CMD_RELAY_OFF2,
    CMD_OPEN,
    CMD_CLOSE,
    CMD_STOP,
    CMD_PLUG_SWITCH_TYPE,
    CMD_LIGHT_SWITCH_TYPE,
    CMD_LIGHT_DIMMER_TYPE,
    CMD_LIGHT_EFFECT_TYPE,
    BLE_DATA_FORMAT 
)

def make_ble_command_data(type_id, stype_id, mac_address, command, data):
    """
    Args :
        type_id: The Pixie device type id as a number.
        stype_id: The Pixie device stype id as a number.
        address: The destination Pixie device mac address as a string.
        command: The command as a string.
        data: The parameters for the command as object.
    """
    pixie_device_spec = PIXIE_DEVICES_SPECS.get(type_id, {}).get(stype_id, None)
    if pixie_device_spec is None:
        raise ValueError(f"Invalid device type ({type_id}) or stype ({stype_id})")
    
    command_dest = mac_address.replace (":","")
    command_type = None
    command_id = pixie_device_spec["command_ids"].get(command, None)
    command_data = None
    
    if pixie_device_spec["light_switch"] and not pixie_device_spec["light_dimmer"]:
        command_type = CMD_LIGHT_SWITCH_TYPE
    elif pixie_device_spec["light_dimmer"]:
        command_type = CMD_LIGHT_DIMMER_TYPE
    elif pixie_device_spec["relay"] > 0 or pixie_device_spec["gpo"] > 0 or pixie_device_spec["usb"] > 0:
        command_type = CMD_PLUG_SWITCH_TYPE
        
    ble_data = BLE_DATA_FORMAT.replace("{{DEST}}", command_dest)
    ble_data = ble_data.replace("{{CMD_TYPE}}", command_type)
    ble_data = ble_data.replace("{{CMD_ID}}", command_id)
    ble_data = ble_data.replace("{{STATE}}", command_data)
    ble_data = ble_data.replace("-", "")
    ble_data = ble_data.rjust(40, '0')

    return ble_data
