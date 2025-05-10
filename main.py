from dotenv import load_dotenv
load_dotenv()

from presentation.terminal import TerminalInterface

THREAD_ID = "main_short_term_memory"

if __name__ == '__main__':
    terminal = TerminalInterface()

    terminal.initialize_terminal(THREAD_ID)
