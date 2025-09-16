# Streamlit

To set the environment, execute the following command:
```bash
python3 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Execute with development mode:
```bash
streamlit run main.py
```

Execute with production mode:
```bash
docker compose up -d --build
```