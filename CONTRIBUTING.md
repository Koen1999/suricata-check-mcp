# Contributing

The `suricata-check-mcp` project is actively maintained and welcomes new contributions in the form of issues and PRs. The project maintains quality-standards for the codebase using CI/CD workflows and review processes to ensure the code remains maintainable for current and future contributors.

The project explicitly welcomes the following types of contributions:

- Improving the overall quality of the codebase (e.g., refining functionality or tests)
- Enhancing CI/CD workflows *(discuss first in an issue)*
- Improving the existing documentation
- [Proposing new features](https://github.com/Koen1999/suricata-check-mcp/issues), such as new MCP tools, that are in-line with current project goals *(discuss first in an issue)*

Note that the rule checks themselves are implemented in [`suricata-check`](https://github.com/Koen1999/suricata-check). Contributions concerning new or existing rule issues should therefore be directed to that project instead.

When in doubt whether a contribution is a good fit for the project, you are encouraged to open or comment on an issue so the maintainers can provide clarifications.

If you would like to contribute, below you can find some helpful suggestions and instructions.

## Reporting bugs

To report a bug you encountered, please open an issue in the [issues](https://github.com/Koen1999/suricata-check-mcp/issues/new) section. You are requested to include a minimal example of when the bug occurs, such that we can reproduce the issue. Where relevant, please mention the MCP client you are using and the transport (e.g., `stdio` or `http`).

## Installing from source

To install `suricata-check-mcp` from source (potentially with local modifications), simply run the following commands:

```bash
git clone https://github.com/Koen1999/suricata-check-mcp
cd suricata-check-mcp
pip install .
```

## Preparing the development environment

To install packages required for running tests and linting, run the following command:

```bash
pip install pip-tools
pip-compile --all-extras -o requirements-dev.txt pyproject.toml
pip install -r requirements-dev.txt
```

Note that you may want to setup a [virtual environment (venv)](https://docs.python.org/3/library/venv.html) before installing dependencies to prevent conflicts.

## Running tests

To run the tests, use the following command:

```bash
pytest
```

Besides tests calling the tools directly and through an in-memory MCP client, the test suite also launches the server as a subprocess and communicates with it over the `stdio` transport, as an MCP client would.

### Inspecting test coverage

Test coverage is automatically assessed when running tests. To inspect the coverage, open `htmlcov/index.html` in your browser and navigate from there.

## Linting

To automatically fix some linting issues and check for remaining issues, run the following commands:

```bash
black .
ruff check . --fix
pyright
```

### Markdownlint

If you made changes to `.md` file and want to lint them locally, you have to install `markdownlint` using `npm`.

```bash
npm install -g markdownlint-cli2
```

Now you can lint markdown files using to automatically detect all issues and fix some:

```bash
markdownlint-cli2 --fix "**/*.md"
```

## Docs

To automatically generate the documentation from the code, run the following commands:

```bash
./docs/make.bat clean
./docs/make.bat html
```

To locally view the docs, run the following command:

```bash
python -m http.server -b localhost -d docs/_build/html 8000
```

and inspect the docs at `localhost:8000`

## Pull requests

When you create a pull request (PR), several checks are automatically run. These include some basic code style checks, as well as running all tests. PRs that do not pass these checks will not be merged. Additionally, PRs will undergo atleast one round of feedback before merging and require approval of atleast one contributor.

PRs should have a clean commit history and have a singular focus since changelogs are automatically generated from PR names. If your PR introduces new tools, functions or classes, tests and documentation should be included where appropriate.

PRs that satisfy the quality criteria of the project (e.g., pass automated CI/CD workflows) and receive one approving review from a maintainer will be merged as long as they are in-line with the current goals of the project.

## Distribution and publication

Releases are fully automated by the `Python Release` workflow (`.github/workflows/python-release.yml`), which runs when a GitHub release is published.

1. **Tag and release**: Create a tag following the existing scheme (e.g. `0.1.0-beta`) and publish a GitHub release for it. The package version is derived from the tag by `setuptools-git-versioning` (`0.1.0-beta` becomes `0.1.0b0`).
2. **PyPI**: The workflow tests and builds the package and publishes it to PyPI using trusted publishing (the `pypi` environment must be configured as a trusted publisher on PyPI).
3. **MCP Registry**: After the PyPI upload, the workflow sets the release version in `server.json`, authenticates with `mcp-publisher login github-oidc`, and publishes the server to the [MCP Registry](https://registry.modelcontextprotocol.io) as `io.github.koen1999/suricata-check-mcp`. Ownership of the PyPI package is verified through the `mcp-name:` comment at the top of `README.md`, which must therefore not be removed.

To publish manually instead, install `mcp-publisher` from the [registry releases](https://github.com/modelcontextprotocol/registry/releases), update the versions in `server.json`, and run `mcp-publisher login github` followed by `mcp-publisher publish`.
