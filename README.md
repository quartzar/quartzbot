# quartzbot
WIP Discord Bot written in Python

## Repository structure

```commandline
quartzbot/
├── src/
│   ├── __init__.py
│   ├── bot.py
│   └── cogs/
│       └── __init__.py
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

## Setup
### Environment file

Create a `.env` file at the repository root. This is essential as otherwise the bot will be have no way of connecting to Discord. 

Example `.env` file:
```
DISCORD_TOKEN=foo
```

### Development
#### Create virtual environment

Create a virtual environment for the project. PyCharm can do this (add a local interpreter option), otherwise:
```bash
cd quartzbot
python3 -m venv venv
```

Activate the virtual environment from repository root like so:
```bash
source venv/bin/activate
```
#### Install requirements

Preferred method is with `uv` rather than `pip`:
```bash
pip install uv
uv pip install -r requirements/base.txt -r requirements/development.txt
```

#### Updating requirements

When adding new requirements, first add the package name to [base.in](requirements/base.in) or [development.in](requirements/development.in)

To compile the requirements:
```bash
uv pip compile --generate-hashes requirements/base.in -o requirements/base.txt
uv pip compile --generate-hashes requirements/development.in -o requirements/development.txt
```

