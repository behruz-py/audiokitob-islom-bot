import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in .env file!")

ADMINS = [int(s) for s in os.getenv("ADMINS", "").split(",") if s.strip()]
DEV_USERNAME = os.getenv("DEV_USERNAME")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
