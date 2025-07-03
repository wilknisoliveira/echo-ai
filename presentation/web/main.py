from dotenv import load_dotenv

from interface.web_interface import WebInterface


load_dotenv()

THREAD_ID = "429117eb-2230-429a-a0ec-76a84a5068ae"
USER_ID = "main_profile"
IS_TERMINAL: bool = False

if __name__ == '__main__':
    web_interface = WebInterface(THREAD_ID, USER_ID)
    web_interface.build_interface()

