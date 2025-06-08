import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEBUG = not hasattr(sys.modules["__main__"], "__compiled__")

if not DEBUG:
    ROOT_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))

API_PORT = 23888

CHROMIUM_EXECUTABLE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"