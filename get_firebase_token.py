import firebase_admin
from firebase_admin import credentials, auth

# Path ke file service account Firebase (taskmaster-sa.json)
cred = credentials.Certificate('C:\\keys\\taskmaster-ai-6ae5f-firebase-adminsdk-fbsvc-965c463001.json')

firebase_admin.initialize_app(cred)

# Verifikasi ID token Firebase
def get_id_token(email: str, password: str):
    # Login menggunakan email dan password (atau bisa menggunakan Firebase SDK di front-end untuk dapatkan token)
    try:
        user = auth.get_user_by_email(email)
        id_token = auth.create_custom_token(user.uid)  # Menggunakan custom token jika diperlukan
        return id_token
    except Exception as e:
        print(f"Error: {e}")
        return None

# Ganti dengan email/password yang valid untuk mendapatkan ID token
email = 'mathxire@gmail.com'
password = 'jeky666'  # Jika menggunakan login email/password
token = get_id_token(email, password)
print("Firebase ID Token:", token)
