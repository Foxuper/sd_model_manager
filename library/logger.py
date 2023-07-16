import sys
import logging
from enum import Enum

# Library
from library.settings import Settings
from library.paths import LOGGER_FILE
from library.settings import EXTENSION_NAME

# Logger state
LOGGER_INITIALIZED = False
FILE_HANDLER: logging.FileHandler | None = None

# Logging formats
DATE_FORMAT     = '%d/%m/%Y %H:%M:%S'
TERMINAL_FORMAT = f'[{EXTENSION_NAME}]: %(message)s'
FILE_FORMAT     = '[%(asctime)-19s] [%(levelname)-8s]: %(message)s'

class TerminalColor(Enum):
	''' Colors for the terminal '''

	GREY     = '\x1b[38;5;248m'
	BLUE     = '\x1b[38;5;39m'
	YELLOW   = '\x1b[38;5;226m'
	RED      = '\x1b[38;5;196m'
	BOLD_RED = '\x1b[31;1m'
	RESET    = '\x1b[0m'

	def wrap(self, text: str):
		return self.value + text + TerminalColor.RESET.value

class ConsoleFormatter(logging.Formatter):
	''' Allows console logs to be formatted with colors '''

	def __init__(self, format: str):
		super().__init__()
		self.fmt = format
		self.formats = \
		{
			logging.DEBUG:    TerminalColor.GREY.wrap(self.fmt),
			logging.INFO:     TerminalColor.BLUE.wrap(self.fmt),
			logging.WARNING:  TerminalColor.YELLOW.wrap(self.fmt),
			logging.ERROR:    TerminalColor.RED.wrap(self.fmt),
			logging.CRITICAL: TerminalColor.BOLD_RED.wrap(self.fmt)
		}

	def format(self, record: logging.LogRecord):
		format = self.formats.get(record.levelno)
		formatter = logging.Formatter(format)
		return formatter.format(record)

def configure():
	'''
		Configures the logs to redirect them to the standard output and to a file
		- Returns the logger instance
	'''
	global LOGGER_INITIALIZED, FILE_HANDLER

	# The logger is created
	logger = logging.getLogger(EXTENSION_NAME)

	# The logger level is set
	logger.setLevel(logging.DEBUG if Settings.debug_mode() else logging.INFO)

	if Settings.debug_mode():
		if FILE_HANDLER is None:

			# Logs are redirected to a file if the debug mode is enabled
			FILE_HANDLER = logging.FileHandler(LOGGER_FILE)
			FILE_HANDLER.setFormatter(logging.Formatter(FILE_FORMAT, DATE_FORMAT))
			logger.addHandler(FILE_HANDLER)
	elif FILE_HANDLER is not None:

			# The file handler is removed if it exists
			logger.removeHandler(FILE_HANDLER)
			FILE_HANDLER = None

	# The logger is returned if it has already been initialized
	if LOGGER_INITIALIZED:
		return logger

	# Logs are redirected to the standard output
	stdout_handler = logging.StreamHandler(sys.stdout)
	stdout_handler.setFormatter(ConsoleFormatter(TERMINAL_FORMAT))
	logger.addHandler(stdout_handler)

	LOGGER_INITIALIZED = True
	return logger