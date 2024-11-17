from invoke import task


@task
def reformat(c):
    # Run ruff check first to sort imports (like isort)
    c.run("ruff check --fix", pty=True)
    # Then run the formatter
    c.run("ruff format", pty=True)
