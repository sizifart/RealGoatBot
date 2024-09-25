from .logger import logger
from . import launcher, date_utils


import os

if not os.path.exists(path="sessions"):
    os.mkdir(path="sessions")
