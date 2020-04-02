import threading
import os
import subprocess

from botui.bot_languages import PillDora
from server.reminders import Reminder


def run_threaded(job_func):
    job_thread = threading.Thread(target=job_func)
    job_thread.start()


if __name__ == "__main__":
    pilldora = PillDora()
    run_threaded(Reminder(pilldora).daily_actualizations)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/home/paesav/prueba/botprueba/TelegramTranscription-emebe.json" #adds the json file that allows the system to query the diagloflow api
    pilldora.main()
