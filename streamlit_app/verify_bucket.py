from supabase import create_client
import os

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

try:
    # Liste tous les buckets
    buckets = supabase.storage.list_buckets()
    
    # Vérifie l'existence
    exists = any(b.name == "pitch-videos" for b in buckets)
    
    if exists:
        print("✅ Vérification réussie : Le bucket existe")
    else:
        print("❌ Le bucket n'a pas été trouvé")

except Exception as e:
    print(f"Erreur de vérification : {str(e)}")
