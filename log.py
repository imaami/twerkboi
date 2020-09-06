import sys

class color:
	reset   = '\033[0m'
	black   = ['\033[30m', '\033[90m']
	red     = ['\033[31m', '\033[91m']
	green   = ['\033[32m', '\033[92m']
	yellow  = ['\033[33m', '\033[93m']
	blue    = ['\033[34m', '\033[94m']
	magenta = ['\033[35m', '\033[95m']
	cyan    = ['\033[36m', '\033[96m']
	white   = ['\033[37m', '\033[97m']

def black(s, bright: int = 0): return color.black[bright] + s + color.reset
def red(s, bright: int = 0): return color.red[bright] + s + color.reset
def green(s, bright: int = 0): return color.green[bright] + s + color.reset
def yellow(s, bright: int = 0): return color.yellow[bright] + s + color.reset
def blue(s, bright: int = 0): return color.blue[bright] + s + color.reset
def magenta(s, bright: int = 0): return color.magenta[bright] + s + color.reset
def cyan(s, bright: int = 0): return color.cyan[bright] + s + color.reset
def white(s, bright: int = 0): return color.white[bright] + s + color.reset

def stdout(s): print(s, file=sys.stdout)
def stderr(s): print(s, file=sys.stderr)

def debug(s): stderr(cyan(s))
def info(s): stderr(cyan(s, 1))
def warn(s): stderr(yellow(s, 1))
def error(s): stderr(red(s, 1))
