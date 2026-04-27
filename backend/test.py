from dotenv import load_dotenv
import os

load_dotenv()  # loads .env from current directory

print("GITHUB_APP_PRIVATE_KEY_PATH =", os.getenv("GITHUB_APP_PRIVATE_KEY_PATH"))

