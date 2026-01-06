import bcrypt

# Tu contraseña real
password_real = "VacaMuerta2026"

# Generamos el hash usando bcrypt directamente
# 1. Convertimos la contraseña a bytes
bytes = password_real.encode('utf-8')
# 2. Generamos la 'sal' (salt) y el hash
salt = bcrypt.gensalt()
hashed = bcrypt.hashpw(bytes, salt)

print(f"Tu contraseña encriptada es: {hashed.decode('utf-8')}")