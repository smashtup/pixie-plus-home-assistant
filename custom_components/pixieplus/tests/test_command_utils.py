import pytest
from unittest.mock import patch
from custom_components.pixieplus.command_utils import make_ble_command_data

class TestMakeBleCommandData:
    """Tests for make_ble_command_data function."""

    @pytest.fixture
    def mock_specs(self):
        """Mock PIXIE_DEVICES_SPECS."""
        return {
            1: {
                1: {
                    "light_switch": True,
                    "light_dimmer": False,
                    "relay": 0,
                    "gpo": 0,
                    "usb": 0,
                    "command_ids": {
                        "on": "01",
                        "off": "02",
                    }
                }
            },
            2: {
                1: {
                    "light_switch": False,
                    "light_dimmer": True,
                    "relay": 0,
                    "gpo": 0,
                    "usb": 0,
                    "command_ids": {
                        "set_brightness": "03",
                    }
                }
            }
        }

    @patch('custom_components.pixieplus.command_utils.PIXIE_DEVICES_SPECS')
    @patch('custom_components.pixieplus.command_utils.BLE_DATA_FORMAT', '{{DEST}}-{{CMD_TYPE}}-{{CMD_ID}}-{{STATE}}')
    @patch('custom_components.pixieplus.command_utils.CMD_LIGHT_SWITCH_TYPE', 'SWITCH')
    def test_light_switch_command(self, mock_specs_dict, mock_specs):
        """Test light switch command generation."""
        mock_specs_dict.__getitem__.return_value.__getitem__.return_value = mock_specs[1][1]
        
        result = make_ble_command_data(1, 1, "AA:BB:CC:DD:EE:FF", "on", None)
        
        assert "AABBCCDDEEFF" in result
        assert "SWITCH" in result
        assert "01" in result

    @patch('custom_components.pixieplus.command_utils.PIXIE_DEVICES_SPECS')
    def test_invalid_device_type(self, mock_specs_dict):
        """Test with invalid device type."""
        mock_specs_dict.get.return_value = {}
        
        with pytest.raises(ValueError, match="Invalid device type"):
            make_ble_command_data(999, 1, "AA:BB:CC:DD:EE:FF", "on", None)

    @patch('custom_components.pixieplus.command_utils.PIXIE_DEVICES_SPECS')
    def test_invalid_stype(self, mock_specs_dict):
        """Test with invalid stype."""
        mock_specs_dict.get.return_value = {}
        
        with pytest.raises(ValueError, match="Invalid device type"):
            make_ble_command_data(1, 999, "AA:BB:CC:DD:EE:FF", "on", None)

    @patch('custom_components.pixieplus.command_utils.PIXIE_DEVICES_SPECS')
    @patch('custom_components.pixieplus.command_utils.BLE_DATA_FORMAT', '{{DEST}}-{{CMD_TYPE}}-{{CMD_ID}}-{{STATE}}')
    @patch('custom_components.pixieplus.command_utils.CMD_LIGHT_DIMMER_TYPE', 'DIMMER')
    def test_light_dimmer_command(self, mock_specs_dict, mock_specs):
        """Test light dimmer command generation."""
        mock_specs_dict.get.return_value.__getitem__.return_value = {
            "light_switch": False,
            "light_dimmer": True,
            "relay": 0,
            "gpo": 0,
            "usb": 0,
            "command_ids": {"set_brightness": "03"}
        }
        
        result = make_ble_command_data(2, 1, "AA:BB:CC:DD:EE:FF", "set_brightness", None)
        
        assert "DIMMER" in result

    @patch('custom_components.pixieplus.command_utils.PIXIE_DEVICES_SPECS')
    @patch('custom_components.pixieplus.command_utils.BLE_DATA_FORMAT', '{{DEST}}-{{CMD_TYPE}}-{{CMD_ID}}-{{STATE}}')
    @patch('custom_components.pixieplus.command_utils.CMD_PLUG_SWITCH_TYPE', 'PLUG')
    def test_plug_switch_command(self, mock_specs_dict, mock_specs):
        """Test plug switch command generation."""
        mock_specs_dict.get.return_value.__getitem__.return_value = {
            "light_switch": False,
            "light_dimmer": False,
            "relay": 1,
            "gpo": 0,
            "usb": 0,
            "command_ids": {"on": "01"}
        }
        
        result = make_ble_command_data(3, 1, "AA:BB:CC:DD:EE:FF", "on", None)
        
        assert "PLUG" in result

    @patch('custom_components.pixieplus.command_utils.PIXIE_DEVICES_SPECS')
    @patch('custom_components.pixieplus.command_utils.BLE_DATA_FORMAT', '0000{{DEST}}{{CMD_TYPE}}{{CMD_ID}}{{STATE}}')
    @patch('custom_components.pixieplus.command_utils.CMD_LIGHT_SWITCH_TYPE', 'AA')
    def test_mac_address_formatting(self, mock_specs_dict):
        """Test MAC address is formatted correctly (colons removed)."""
        mock_specs_dict.get.return_value.__getitem__.return_value = {
            "light_switch": True,
            "light_dimmer": False,
            "relay": 0,
            "gpo": 0,
            "usb": 0,
            "command_ids": {"on": "01"}
        }
        
        result = make_ble_command_data(1, 1, "AA:BB:CC:DD:EE:FF", "on", None)
        
        assert "AABBCCDDEEFF" in result
        assert ":" not in result

    @patch('custom_components.pixieplus.command_utils.PIXIE_DEVICES_SPECS')
    @patch('custom_components.pixieplus.command_utils.BLE_DATA_FORMAT', 'ABC')
    @patch('custom_components.pixieplus.command_utils.CMD_LIGHT_SWITCH_TYPE', 'XX')
    def test_output_padding(self, mock_specs_dict):
        """Test output is padded to 40 characters."""
        mock_specs_dict.get.return_value.__getitem__.return_value = {
            "light_switch": True,
            "light_dimmer": False,
            "relay": 0,
            "gpo": 0,
            "usb": 0,
            "command_ids": {"on": "01"}
        }
        
        result = make_ble_command_data(1, 1, "AA:BB:CC:DD:EE:FF", "on", None)
        
        assert len(result) == 40