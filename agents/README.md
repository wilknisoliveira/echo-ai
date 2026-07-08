# echo-ai-agent

To set the environment, execute the following command:

```bash
py -m venv .venv
venv\Scripts\activate
pip install -e .
```

Or using uv:

```bash
uv sync
uv sync --group dev
```

## Install new dependencies

### Using uv (recommended)

```bash
uv add <package-name>
```

To add a dev dependency:

```bash
uv add --group dev <package-name>
```

After adding, run `uv sync` to update the environment:

```bash
uv sync
```

### Using pip

Activate the virtual environment first, then:

```bash
.venv\Scripts\activate
pip install <package-name>
```

> **Note:** If you add a dependency that should be permanent, add it to `[project.dependencies]` in `pyproject.toml` as well.

Execute with development mode:

```bash
.venv\Scripts\activate
langgraph dev
```

To run the agent with docker, execute the following command:

```bash
docker compose up -d --build
```

# Dockerfile

The `langgraph dockerfile` command translates all the configuration in your `langgraph.json` file into Dockerfile commands. When using this command, you will have to re-run it whenever you update your langgraph.json file. Otherwise, your changes will not be reflected when you build or run the dockerfile.

# Generate new thread

POST http://localhost:{PORT}/threads
body: {}
