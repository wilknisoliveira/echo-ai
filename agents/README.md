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
