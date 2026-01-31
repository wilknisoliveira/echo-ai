# echo-ai-agent

To set the environment, execute the following command:

```bash
py -m venv venv
venv\Scripts\activate
pip install -e .
```

Execute with development mode:

```bash
venv\Scripts\activate
langgraph dev
```

To run the agent with docker, execute the following command:

```bash
docker compose up -d --build
```
