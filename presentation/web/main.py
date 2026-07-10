from dotenv import load_dotenv
from interface.web_interface import WebInterface  # noqa: E402

load_dotenv()

USER_ID = "main_profile"
DEBUG: bool = __import__("os").environ.get("DEBUG", "").lower() == "true"

if __name__ == '__main__':
    web_interface = WebInterface(USER_ID, debug=DEBUG)
    web_interface.build_interface()

