from dotenv import load_dotenv

from presentation.web.web_interface import WebInterface


load_dotenv()

THREAD_ID = "main_short_term_memory"
USER_ID = "main_profile"
IS_TERMINAL: bool = False

if __name__ == '__main__':
    web_interface = WebInterface(THREAD_ID, USER_ID)
    web_interface.build_interface()

