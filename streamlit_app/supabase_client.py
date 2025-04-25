import streamlit as st
from supabase import create_client
from openai import OpenAI

# Configuration des clients
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]

# Initialisation
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

def get_user_profile(user_id: str) -> dict:
    """Récupère le profil DISC depuis Supabase"""
    response = supabase.table("users").select("disc_profile").eq("id", user_id).execute()
    return response.data[0] if response.data else None

def get_rag_context(query: str, profile: str) -> list:
    """Recherche contextuelle avec embeddings"""
    embedding = openai_client.embeddings.create(
        input=query,
        model="text-embedding-3-small"
    ).data[0].embedding
    
    results = supabase.rpc("search_context", {
        "query_embedding": embedding,
        "similarity_threshold": 0.75,
        "match_count": 3,
        "profile_filter": profile
    }).execute()
    
    return [item["content"] for item in results.data]
