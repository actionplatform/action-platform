"""Devtool CLI entrypoint."""

from devtool.cli.setup import app


def main() -> None:
    app()


if __name__ == "__main__":
    main()
