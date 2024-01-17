# Must inverter integration for Home Assistant

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
![Project Maintenance][maintenance-shield]

[![Buy me a coffee!](https://www.buymeacoffee.com/assets/img/custom_images/black_img.png)][buymecoffee]

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=mukaschultze&repository=ha-must-inverter)

<!-- [![Discord][discord-shield]][discord] -->
<!-- [![Community Forum][forum-shield]][forum] -->

The Home Assistant Must Solar Inverter Plugin is a custom integration that adds support for monitoring and controlling
Must solar inverters within the Home Assistant platform. This plugin enables you to retrieve real-time data, such as
power production, battery status, and more, directly from your Must solar inverter.

## Features

- **Real-time Monitoring**: View live data from your Must solar inverter, including power production, battery status, and other relevant information.
- **Integration with Home Assistant**: Seamlessly integrate Must solar inverter data into your Home Assistant setup.
- **Control Functionality**: Control certain aspects of your Must solar inverter directly through Home Assistant.

![image](https://gist.github.com/assets/13923364/5bfa1053-c0e7-4e59-b9a8-d94005783263)
![image](https://gist.github.com/assets/13923364/42cae6d8-f903-4d2b-be65-062c89c8fdfb)

## Installation

### HACS (Home Assistant Community Store)

If you have HACS just search for `Must Inverter` and install it from there. Or alternatively, [click here](https://my.home-assistant.io/redirect/hacs_repository/?owner=mukaschultze&repository=ha-must-inverter).

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
5. Enter the required configuration for your serial setup (USB, TCP, or UDP).

![image](https://gist.github.com/assets/13923364/bbad3388-2441-4e01-b377-22e200783777)

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
