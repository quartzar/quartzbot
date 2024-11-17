# quartzbot

*WIP Discord Bot written in Python*

### Repository structure

```
quartzbot/
├── compose.yaml
├── Dockerfile
├── LICENSE
├── README.md
├── requirements
│   ├── base.in
│   ├── base.txt
│   ├── development.in
│   └── development.txt
└── src
    ├── __init__.py
    ├── bot.py
    ├── cache.py
    ├── cogs
    │   ├── __init__.py
    │   ├── music
    │   │   ├── __init__.py
    │   │   ├── cog.py
    │   │   └── views.py
    │   ├── text
    │   │   ├── __init__.py
    │   │   └── cog.py
    │   └── voice
    │       ├── __init__.py
    │       └── cog.py
    ├── main.py
    └── utils.py

```

## Setup
### Environment file

Create a `.env` file at the repository root. This is essential as otherwise the bot will be have no way of connecting to Discord. 

Example `.env` file (also see [.env.example](.env.example)):
```
DISCORD_TOKEN=foo
GUILD_ID=bar
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

#### Running the bot

Once you have set up your dev environment, start the bot like so:

```bash
docker compose up --build
# use `-d` to detach 
```
