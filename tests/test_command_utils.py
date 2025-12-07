import pytest
from custom_components.pixieplus import command_utils as cmd_utils
from custom_components.pixieplus.const import (
    CMD_ON,
    CMD_SET_BRIGHTNESS,
    CMD_LIGHT_DIMMER_TYPE,
)


class TestCommandUtils:
    """Tests for make_ble_command_data function."""

    def test_invalid_device_type(self):
        """Test with invalid device type."""

        with pytest.raises(ValueError, match="Invalid device type"):
            cmd_utils.device_spec(999, 1)

    def test_invalid_device_stype(self):
        """Test with invalid stype."""

        with pytest.raises(ValueError, match="Invalid device type"):
            cmd_utils.device_spec(1, 999)

    def test_invalid_device_command_id(self):
        """Test with invalid command for device."""

        with pytest.raises(
            ValueError, match="Command 'set_brightness' has no mapping for device"
        ):
            cmd_utils.device_command_id(22, 13, CMD_SET_BRIGHTNESS)

    def test_valid_device_id_to_hex_format(self):
        """Test device ID to hex conversion."""

        result = cmd_utils.device_id_to_hex(215)

        assert "d7" in result
        assert len(result) == 2

    def test_valid_command_type_lookup(self):
        """Test for valid command type lookup."""

        result = cmd_utils.device_command_type(23, 11)

        assert CMD_LIGHT_DIMMER_TYPE in result

    def test_missing_command_type_lookup(self):
        """Test for missing command type lookup."""

        with pytest.raises(
            ValueError, match="Cannot determine command type for device type 1 stype 2"
        ):
            cmd_utils.device_command_type(1, 2)

    def test_output_padding(self):
        """Test output is padded to 40 characters."""

        result = cmd_utils.make_ble_command_data(22, 13, 10, CMD_ON, None)

        assert len(result) == 40

    def test_light_switch_command(self):
        """Test light switch command generation."""

        result = cmd_utils.make_ble_command_data(22, 13, 1, CMD_ON, None)

        assert "00000003040100ed696901000000000000000000" in result

    def test_plug_switch_command(self):
        """Test plug switch command generation."""

        result = cmd_utils.make_ble_command_data(1, 7, 1, CMD_ON, None)

        assert "00000003040100c1696903000000000000000000" in result
