# Streamlit

To set the environment, execute the following command:
```bash
py -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Execute with development mode:
```bash
venv\Scripts\activate
streamlit run main.py
```

Execute with production mode:
```bash
docker compose up -d --build
```