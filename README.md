# project-deploy-kit
Magical project deployer that handles verisoning, building, and publishing

## Installation

Download the latest release and put `pdk.py` into the root directory of your project.

Installation via PIP is planned.

## How to Use

```sh
❯ python3 pdk.py -h
usage: pdk.py [-h] [-n] [{build-only,publish}]

positional arguments:
  {build-only,publish}  action to perform

options:
  -h, --help            show this help message and exit
  -n, --no-bump         build the extension without bumping patch version
```

By default, PDK is run in `build-only` mode. For publishing, run in `publish` mode.

### Project Settings

Set project settings in `pdk.properties`, see this repo for an example of how that should look.