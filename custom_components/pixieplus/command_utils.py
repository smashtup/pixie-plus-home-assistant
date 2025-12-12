from .const import (
    PIXIE_DEVICES_SPECS,
    CMD_PLUG_SWITCH_TYPE,
    CMD_LIGHT_SWITCH_TYPE,
    CMD_LIGHT_DIMMER_TYPE,
    CMD_BLE_DATA_FORMAT,
)


def make_ble_command_data(type_id, stype_id, device_id, command, data):
    """
    Args :
        type_id: The Pixie device type id as a number.
        stype_id: The Pixie device stype id as a number.
        device_id: The destination Pixie device id as a number.
        command: The command as a string.
        data: The parameters for the command as object.
    """
    command_id = device_command_id(type_id, stype_id, command)
    command_type = device_command_type(type_id, stype_id, command)
    command_dest = device_id_to_hex(device_id)

    command_data = ""
    if data is not None:
        command_data = f"{data}"

    ble_data = construct_ble_data_str(
        command_dest, command_type, command_id, command_data
    )

    return ble_data


def construct_ble_data_str(command_dest, command_type, command_id, command_data):
    ble_data = CMD_BLE_DATA_FORMAT.replace("{{DEST}}", command_dest)
    ble_data = ble_data.replace("{{CMD_TYPE}}", command_type)
    ble_data = ble_data.replace("{{STATE}}", command_data)
    ble_data = ble_data.replace("{{CMD_ID}}", command_id)
    ble_data = ble_data.replace("-", "")
    ble_data = ble_data.ljust(40, "0")
    return ble_data


def device_spec(type_id, stype_id):
    pixie_device_spec = PIXIE_DEVICES_SPECS.get(type_id, {}).get(stype_id, None)
    if pixie_device_spec is None:
        raise ValueError(f"Invalid device type ({type_id}) or stype ({stype_id})")

    return pixie_device_spec


def device_id_to_hex(device_id):
    return f"{device_id:02x}"


def device_command_type(type_id, stype_id, command):
    pixie_device_spec = device_spec(type_id, stype_id)
    command_type = None
    if pixie_device_spec["light_switch"] and (
        not pixie_device_spec["light_dimmer"] or command in ["on", "off"]
    ):
        command_type = CMD_LIGHT_SWITCH_TYPE
    elif pixie_device_spec["light_dimmer"]:
        command_type = CMD_LIGHT_DIMMER_TYPE
    elif (
        pixie_device_spec["relay"] > 0
        or pixie_device_spec["gpo"] > 0
        or pixie_device_spec["usb"] > 0
    ):
        command_type = CMD_PLUG_SWITCH_TYPE

    if command_type is None:
        raise ValueError(
            f"Cannot determine command type for device type {type_id} stype {stype_id}"
        )
    return command_type


def device_command_id(type_id, stype_id, command):
    command_id = device_spec(type_id, stype_id)["command_ids"].get(command, None)
    if command_id is None:
        raise ValueError(
            f"Command '{command}' has no mapping for device type {type_id} stype {stype_id}"
        )

    return command_id
