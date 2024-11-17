from pathlib import Path

from invoke import task
from rich.console import Console

console = Console()


@task
def reformat(c):
    # Run ruff check first to sort imports (like isort)
    c.run("ruff check --fix", pty=True)
    # Then run the formatter
    c.run("ruff format", pty=True)


@task
def update_requirements(c, upgrade: bool = False):
    # Find all requirements files under ./requirements/
    directory = Path.joinpath(Path(__name__).parent, "requirements")
    input_files = [str(file) for file in list(directory.glob("*.in"))]
    output_files = [str(file).replace(".in", ".txt") for file in input_files]

    base_cmd = [
        "uv",
        "pip compile",
        "--generate-hashes",
    ]

    if upgrade:
        base_cmd += ["--upgrade"]

    if len(input_files) != len(output_files):
        console.log(
            "ERROR: Input and output requirements files count differs (input: %s, output: %s",
            len(input_files),
            len(output_files),
            style="bold bright_red"
        )
        return

    for i in range(len(input_files)):
        cmd = base_cmd + [
            input_files[i],
            "-o",
            output_files[i],
        ]
        c.run(" ".join(cmd), pty=True)

    console.log("All requirements files successfully updated & compiled!", style="bold bright_green")
