from dotenv import load_dotenv, find_dotenv
from os import environ, _exit

load_dotenv(find_dotenv())
try:
    DB_NAME = environ["DB_NAME"]
    NODE_RPC_URL = environ["NODE_RPC_URL"]
    NODE_WALLET_ID = environ["NODE_WALLET_ID"]
    NODE_ACCOUNT = environ["NODE_ACCOUNT"]
    FAUCET_AMOUNT = environ["FAUCET_AMOUNT"]
    CLAIM_PERIOD = environ["CLAIM_PERIOD"]
    ALLOWED_ROLE = environ.get("ALLOWED_ROLE", None)
    ALLOWED_CHANNEL = environ.get("ALLOWED_CHANNEL", None)
    TOKEN = environ["TOKEN"]
    SUPPORT_ID = environ.get("SUPPORT_ID", None)
    ACTIVITY_NAME = environ["ACTIVITY_NAME"]
except KeyError as e:
    print(f"Could not find a required environment variable ({e}), make sure to set all variables in a .env file (make a copy of .env.sample)")
    _exit(1)
