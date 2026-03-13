import bcrypt
try:
    print(f"Bcrypt version: {bcrypt.__version__}")
    print(f"Bcrypt __about__: {getattr(bcrypt, '__about__', 'Not found')}")
    
    # Try the monkeypatch
    if not hasattr(bcrypt, "__about__"):
        bcrypt.__about__ = type('about', (object,), {'__version__': bcrypt.__version__})
        print(f"Patched Bcrypt __about__.__version__: {bcrypt.__about__.__version__}")
    
    import passlib.handlers.bcrypt
    print("Passlib bcrypt handler loaded successfully")
except Exception as e:
    print(f"Error: {e}")
