# (alpha) PIXIE Plus for Home Assistant

This integration will hopefully serve as a reimplementation(tidy up) of the awesome work @nirnachmani did with [Pixie-Plus-for-Home-Assistant](https://github.com/nirnachmani/Pixie-Plus-for-Home-Assistant). 

> **⚠️ Important Note:**  Unfortunately using this integration **WILL** impact a [Pixie-Plus-for-Home-Assistant](https://github.com/nirnachmani/Pixie-Plus-for-Home-Assistant) install/config on the same Home Assistant Server. You will need to delete the [Pixie-Plus-for-Home-Assistant](https://github.com/nirnachmani/Pixie-Plus-for-Home-Assistant) integration first.


## Overview

Custom integration for Home Assistant that connects with PIXIE Plus smart home products made by [SAL](https://www.pixieplus.com/) (Australia). 

PIXIE offers a suite of Bluetooth Mesh smart home products for controlling various aspects of your home - including lights, blinds, garage doors, gates, fans, and appliances. This integration supports a variety of these devices with capabilities including dimming, colors, effects, and more.

> **⚠️ Important Note:** This integration has been tested on limited systems and may require modifications to work with your setup. While not officially supported, I may be able to provide limited assistance.

## Pixie Devices Currently Supported

- **Smart Switches & Dimmers**
  - Smart Switch G3 (SWL600BTAM)
  - Smart Dimmer G3 (SDD300BTAM)
  - Smart Switch G2 (SWL350BT)
  - Smart Dimmer G2 (SDD350BT)

### Still To Implement/Test

  - rippleSHIELD DIMMER (SDD400SFI)

- **Smart Plugs & Outlets**
  - Smart Plug (ESS105/BT)
  - Smart Socket Outlet (SP023/BTAM)

- **LED & Lighting**
  - Flexi Smart LED Strip (FLP12V2M/RGBBT)
  - Flexi Streamline (FLP24V2M)
  - LED Strip Controller (LT8915DIM/BT)

- **Control Devices**
  - Dual Relay Control (PC206DR/R/BTAM)
  - Blind & Signal Control (PC206BS/R/BTAM)

## Prerequisites

- A working PIXIE Plus Hub
- All devices must be already set up in the PIXIE Plus app
- Internet connection (local-only mode is not supported)

## Installation Guide

**Highly recommend backing up Home Assistant first before trying this integration.**

### Do you have [HACS](https://hacs.xyz/) installed?
1. Add pixie-plus-home-assistant as custom repository.
  1. Go to: `HACS`
  1. Click on the 3 dots in the top right corner.
  1. Select "Custom repositories"
  1. Add the URL https://github.com/smashtup/pixie-plus-home-assistant to the repository.
  1. Select "Integration" type.
  1. Click the "ADD" button.
  
  1. Search HACs integrations for **Pixie Plus Cloud Control**
  1. Click `Download`
  1. Restart Home Assistant
  1. See Setup for how to add your lights to HA

### Manual Copy
  1. Install this platform by creating a `custom_components` folder in the same folder as your configuration.yaml, if it doesn't already exist.
  1. Create another folder `pixie_plus` in the `custom_components` folder
  1. Copy all files from `custom_components/pixieplus` into the `pixie_plus` folder.


## Setup

1. Add Pixie Plus Cloud Control Integration
  1. Go to Home Assistant → Settings → Devices & Services → Integrations
  1. Click the "ADD INTEGRATION" button
  1. Search for "PIXIE Plus" and select it
  1. You will be prompted to enter your Pixie Plus username and password that you created when you first set up the Pixie Plus App on your Mobile device

## Limitations

- The integration doesn't support PIXIE Plus groups, scenes, schedules, or timers (use Home Assistant for these functions)
- Only works with a PIXIE Plus Hub (doesn't support direct Bluetooth connections)
- Requires cloud connectivity (local-only mode is not currently possible)

## Support

This integration is provided as-is with limited support. Feel free to use, modify, and extend the code as needed for your own setup.
