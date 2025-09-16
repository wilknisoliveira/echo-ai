# echo-ai-agent

To set the environment, execute the following command:
```bash
python3 -m venv venv
venv\Scripts\activate
pip install -e .
```

Execute with development mode:
```bash
langgraph run
```

To run the agent with docker, execute the following command:
```bash
docker compose up -d --build
```