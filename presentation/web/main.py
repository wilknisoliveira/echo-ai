from os import environ

from dotenv import load_dotenv

from interface.web_interface import WebInterface


load_dotenv()

THREAD_ID = environ.get("THREAD_ID")
USER_ID = "main_profile"
IS_TERMINAL: bool = False

if __name__ == '__main__':
    web_interface = WebInterface(THREAD_ID, USER_ID)
    web_interface.build_interface()

