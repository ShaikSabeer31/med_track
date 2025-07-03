# Define the mock_users dictionary at the module level
mock_users = {}

def register_user(username, password, role):
    mock_users[username] = {
        "password": password,
        "role": role
    }

def validate_login(username, password):
    user = mock_users.get(username)
    if user and user['password'] == password:
        return user['role']
    return None


