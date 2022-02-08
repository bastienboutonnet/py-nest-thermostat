## py-nest-thermostat [0.0.5] - 2022-02-08

### Bug Fixes

- [#22](https://github.com/bastienboutonnet/py-nest-thermostat/issues/22) Device stats cards show **after** temperature update when using `nest temp <temperature>` instead of before to reflect the change more accurately and more pleasingly.

## py-nest-thermostat [0.0.4] - 2022-02-08

### Bug Fixes

- [#19](https://github.com/bastienboutonnet/py-nest-thermostat/issues/19) Fixes potential `KeyError`s on accessing properties of device traits that don't exist.

### Features

- [#19](https://github.com/bastienboutonnet/py-nest-thermostat/issues/19) Adds display of eco mode, and uses target temperature of eco mode in case eco mode is on instead of the regular target temperature.

- [#20](https://github.com/bastienboutonnet/py-nest-thermostat/issues/20) User Atom One Dark Pro theme colours because, we like to use pretty tools!

## py-nest-thermostat [0.0.3] - 2021-12-19

### Features

- [#8](https://github.com/bastienboutonnet/py-nest-thermostat/issues/8) **Breaking Change**: CLI application name is renamed from `py-nest` to `nest` for better user experience.

### Under The Hood/Misc

- [#8](https://github.com/bastienboutonnet/py-nest-thermostat/issues/8) **Breaking Change:** Authentication is refactored and users should store their nest authentication information into a `config.yaml` file and place it under the `~/.py-nest-thermostat/` folder. See `config.yaml.sample` for more information.
