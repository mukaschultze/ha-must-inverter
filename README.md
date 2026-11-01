# Must inverter integration for Home Assistant

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
![Project Maintenance][maintenance-shield]

[![Buy me a coffee!](https://www.buymeacoffee.com/assets/img/custom_images/black_img.png)][buymecoffee]

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=mukaschultze&repository=ha-must-inverter&category=integration)

<!-- [![Discord][discord-shield]][discord] -->
<!-- [![Community Forum][forum-shield]][forum] -->

The Home Assistant Must Solar Inverter Plugin is a custom integration that adds support for monitoring and controlling
Must solar inverters within the Home Assistant platform. This plugin enables you to retrieve real-time data, such as
power production, battery status, and more, directly from your Must solar inverter.

## Features

- **Real-time Monitoring**: View live data from your Must solar inverter, including power production, battery status, and other relevant information.
- **Integration with Home Assistant**: Seamlessly integrate Must solar inverter data into your Home Assistant setup.
- **Control Functionality**: Control certain aspects of your Must solar inverter directly through Home Assistant.

| ![image](https://github.com/mukaschultze/ha-must-inverter/assets/13923364/1cc55f7e-dc07-4a83-886c-77b83c2845b8) | ![image](https://github.com/mukaschultze/ha-must-inverter/assets/13923364/0533e262-d9da-4494-ac8d-51298d216e90) |
| :-------------------------------------------------------------------------------------------------------------: | :-------------------------------------------------------------------------------------------------------------: |

## Supported Devices

This integration is tested using a Must Solar PV18-3024 VPM (aka PV1800), PV19 / PV1900 EXP Series (4/6KW), PH11 / PH1100 EU Series (AC:380V 5-12KW). However, it should work with other models that use the same communication protocol, such as the PH1800 and EP1800 series.

## Disclaimer

This integration is not officially supported by Must Solar, I'm not affiliated with Must Solar in any way. This
integration is based on reverse engineering the communication protocol used by the Must Solar inverters and by resources
found online. Use it at your own risk.

> [!CAUTION]
> There are some modbus registers that cannot be reversed to their original value after being written and can have a
> huge effect on the inverter operation, such as the calibration coefficients (these entities are disabled by default).
> This integration **DOES NOT** write any information to the device via modbus unless you manually change an entity value.

## Installation

> [!IMPORTANT]
> Requires **Home Assistant 2026.10 or newer**. The integration talks to the inverter through Home Assistant's shared
> Modbus connections, which also enables ESPHome serial proxies.

### HACS (Home Assistant Community Store)

If you have HACS just search for `Must Inverter` and install it from there. Or alternatively, [click here](https://my.home-assistant.io/redirect/hacs_repository/?owner=mukaschultze&repository=ha-must-inverter&category=integration).

### Manual Installation

1. Download the [latest release](https://github.com/mukaschultze/ha-must-inverter/releases/latest) from the GitHub repository.
2. Extract the downloaded archive.
3. Copy the `custom_components/must_inverter` directory to your Home Assistant config directory.
4. Restart Home Assistant.

After a correct installation, your configuration directory should look like this:

```text
    └── ...
    └── configuration.yaml
    └── secrets.yaml
    └── custom_components
        └── must_inverter
            └── __init__.py
            └── config_flow.py
            └── const.py
            └── ...
```

## Usage

1. Open the Home Assistant UI.
2. Navigate to "Configuration" -> "Integrations."
3. Click the "+" button to add a new integration.
4. Search for "Must Inverter" and select it.
5. Enter the required configuration for your serial setup (USB, TCP, or UDP). The connection is tested before the
   integration is added.

![image](https://github.com/mukaschultze/ha-must-inverter/assets/13923364/92fa79ea-9e4a-4028-8563-9a4fa88a2cfa)

### Connection types

- **USB or Serial**: pick the port from the dropdown. It lists the USB ports plugged into the Home Assistant host and
  any ESPHome serial proxies. The defaults (19200 baud, 8N1, device ID 4) work for most models.
- **Serial device servers**: choose _Enter manually_ in the port dropdown and type a URL. Use `socket://<ip>:<port>`
  for raw TCP bridges (`ser2net`, transparent RS485-to-Wi-Fi converters such as the PW-11), with the baud rate set on
  the bridge itself, or `rfc2217://<ip>:<port>` for bridges that support RFC 2217.
- **TCP / UDP**: for Modbus TCP gateways (e.g. [mbusd](https://github.com/3cky/mbusd) running next to the inverter, or
  a converter in Modbus TCP gateway mode).

### ESPHome serial proxy

Since Home Assistant 2026.5 an ESPHome device can share its serial port with Home Assistant over the network. That
lets you put a small ESP32 with an RS485 transceiver next to the inverter instead of running a USB cable to the Home
Assistant host.

1. Wire the RS485 transceiver to the inverter's RS485 (RJ45) port, using the pinout from your inverter's manual.
2. Flash the ESPHome device with a `uart` and a `serial_proxy` (pins are an example, adjust them to your board):

   ```yaml
   uart:
     - id: rs485_uart
       tx_pin: GPIO16
       rx_pin: GPIO17
       baud_rate: 19200

   api:

   serial_proxy:
     - id: inverter_port
       uart_id: rs485_uart
       name: Must Inverter
       port_type: RS485
       rts_pin: GPIO18 # DE/RE of the transceiver, if it has no automatic direction control
   ```

   See the [ESPHome serial proxy docs](https://esphome.io/components/serial_proxy/) for the full set of options.

3. Add the ESPHome device to Home Assistant, then add Must Inverter, choose **USB or Serial** and pick the port listed
   under **Serial proxies**. Home Assistant applies the baud rate and other serial settings to the proxy, so there's no
   need to change them in ESPHome.

A wired network connection to the proxy is recommended. If the proxy is offline when Home Assistant starts, the
integration keeps retrying until the ESPHome device is back.

<!---->

## Support and Contributions

For bug reports, feature requests, or general questions, please create an issue on the GitHub repository.

Contributions are welcome! Feel free to fork the repository, make changes, and submit a pull request.

## Acknowledgments

This plugin would not have been possible without the valuable contributions of the following individuals and their projects on reversing engineering the Must solar inverter:

- https://github.com/aquarat/must_inverter
- https://github.com/dylangmiles/docker-must-homeassistant
- https://github.com/thelabexpedition67/MustInverterDataHandler

Their efforts have paved the way for the development of this Home Assistant integration.

## License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details.

---

[integration_blueprint]: https://github.com/mukaschultze/ha-must-inverter
[buymecoffee]: https://www.buymeacoffee.com/mukaschultze
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge
[commits-shield]: https://img.shields.io/github/commit-activity/y/mukaschultze/ha-must-inverter.svg?style=for-the-badge
[commits]: https://github.com/mukaschultze/ha-must-inverter/commits/main
[discord]: https://discord.gg/Qa5fW2R
[discord-shield]: https://img.shields.io/discord/330944238910963714.svg?style=for-the-badge
[exampleimg]: example.png
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/github/license/mukaschultze/ha-must-inverter.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40mukaschultze-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/mukaschultze/ha-must-inverter.svg?style=for-the-badge
[releases]: https://github.com/mukaschultze/ha-must-inverter/releases
