import configparser

config = configparser.ConfigParser()
config.read("config.ini")

EXCHANGE = config["DEFAULT"]["EXCHANGE"]
PAIR = config["DEFAULT"]["PAIR"]
TIMEFRAME = config["DEFAULT"]["TIMEFRAME"]
API_KEY = config["DEFAULT"]["API_KEY"]
SECRET = config["DEFAULT"]["SECRET"]
API_KEY_SANDBOX = config["DEFAULT"]["API_KEY_SANDBOX"]
SECRET_SANDBOX = config["DEFAULT"]["API_KEY_SANDBOX"]
