Version: `v0.0.2`

# py-nest-thermostat

Python CLI Nest Controller and Reporting Tool.

**Disclaimer:**
This project is very much work in progress while in version 0 anything can change, anything can break and some parts of the code are probably very ugly. Feel free to test it, contribute (see [CONTRIBUTING.md]()), report bugs

**Get device stats:**
![py nest stats](https://p56.f1.n0.cdn.getcloudapp.com/items/E0uKZLBb/dd63f9ff-a65e-4a95-9067-bc4c6f09d77a.gif?source=viewer&v=3e9c6a77683dd232609d610395417e58)

**Set Device Temperature:**
![py nest set temp](https://p56.f1.n0.cdn.getcloudapp.com/items/E0uKZLBZ/ca47db6b-3d8c-479c-b350-a0fdfd7416b1.gif?source=viewer&v=898e9184fbb67ee4471646039837bae8)

## Features:

- print device stats
- set target temperature

## Future Features:

- capture device statistics into a database
- plot device statistics over time
- some ML?

# Installation

The tool is intallable from [PyPI](https://pypi.org) via `pip` or [`pipx`](https://pypa.github.io/pipx/). But you must first set up access via Google's Developer console (which currently costs a one time $5 fee and is a bit of a pain).

## Set Up Google and Authorization

This part of the process is a real pain, especially if you've never set up Authorization via Google. Luckily [Wouter Nieuwerth](https://www.wouternieuwerth.nl/about/) made a really nice [guide](https://www.wouternieuwerth.nl/controlling-a-google-nest-thermostat-with-python/) with pictures that I encourage you to check out

### Google Documentation Links

Google has some pretty extensive documentation:

- [Nest Getting Started](https://developers.google.com/nest/device-access/get-started)
- [Device Registration](https://developers.google.com/nest/device-access/registration)

Once setup, you will be able to access your nest devicesc, and manage your authorizations in the following places:

- [Nest Device Access](https://console.nest.google.com/device-access/)
- [Google Developers Console](https://console.developers.google.com/)

If you have issues, and neither the [step by step guide from Wouter](https://www.wouternieuwerth.nl/controlling-a-google-nest-thermostat-with-python/) nor the links above help you feel free to open an issue and if I have time I'll try and help out.

## Install `py-nest-thermostat`

If you want to be able to access the tool from anywhere I recomment setting it up via [pipx](https://pypa.github.io/pipx/). Pipx will give you access to `py-nest` globally while keeping it in an isolated python virtual environment. The best of both worlds really!

You can install with pipx like so:

```bash
pipx install py-nest-thermostat
```

## Create your credentials file

`nest` expects your credentials and other handy authentication parameters to be in an file named `config.yaml` and it should be placed at this location `~/.py-nest-thermostat/`. We might implement the possibility to pass a custom location later. If you're too impatient feel free to help out! :)

You can find an example of this file [here](./config.yaml.sample)

If you prefer to use regular `pip`, follow those steps:

1. create a python3 virtual environment (with `venv` or `virtualenv` --up to you)
2. activate the virtual environment (`source /path/to/virtual/environment`)
3. `pip install py-nest-thermostat`

# Usage

Until I write some more extensive docs, once you have installed the tool use use the CLI `--help` command

```bash
nest --help
```
