import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

def create_bucket():
    # Configuration Supabase
    supabase: Client = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY")
    )
    
    # Paramètres du bucket
    bucket_config = {
        "name": "pitch-videos",
        "id": "pitch-videos",  # Doit être identique au nom
        "public": True,
        "file_size_limit": 52428800,  # 50MB en octets
        "allowed_mime_types": ["video/*", "audio/*"]
    }
    
    try:
        # Création du bucket
        response = supabase.storage.create_bucket(bucket_config)
        
        if response.get("id") == "pitch-videos":
            print("✅ Bucket créé avec succès !")
            print(f"Nom : {response['name']}")
            print(f"Statut : {'Public' if response['public'] else 'Privé'}")
        else:
            raise Exception("Réponse inattendue de l'API")

    except Exception as e:
        print(f"❌ Erreur lors de la création : {str(e)}")
        if 'already exists' in str(e):
            print("Solution : Supprimez d'abord le bucket existant via l'interface Supabase")

if __name__ == "__main__":
    create_bucket()
