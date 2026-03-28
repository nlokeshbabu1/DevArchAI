from datetime import datetime, timedelta
from app.core.security import create_access_token

# Create a token for the user
user_id = "9fb9216a-2dd4-40d2-8a8f-add3b1632be8"
username = "nlokeshbabu1"

token_data = {"sub": user_id, "username": username}
token = create_access_token(data=token_data)
print(f"ACCESS_TOKEN={token}")
print(f"Username: {username}")
print(f"User ID: {user_id}")
