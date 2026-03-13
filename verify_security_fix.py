from app.shared.utils.security.security import verify_password, hash_password
import bcrypt

print(f"Bcrypt __about__ present: {hasattr(bcrypt, '__about__')}")

password = "test_password_123"
hashed = hash_password(password)
print(f"Hashed password: {hashed}")

is_valid = verify_password(password, hashed)
print(f"Verification result: {is_valid}")

if is_valid:
    print("SUCCESS: Password verification works with monkeypatch.")
else:
    print("FAILURE: Password verification failed.")
