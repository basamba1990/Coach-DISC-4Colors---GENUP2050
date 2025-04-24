import streamlit as st
from supabase import create_client
import openai

# Configuration
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
openai.api_key = st.secrets["OPENAI_API_KEY"]

def get_rag_context(question: str, profile: str) -> list:
    """Recherche contextuelle vectorielle"""
    # Génération embedding
    embedding = openai.embeddings.create(
        input=question,
        model="text-embedding-3-small"
    ).data[0].embedding
    
    # Requête Supabase
    result = supabase.rpc('search_context', {
        'query_embedding': embedding,
        'similarity_threshold': 0.75,
        'match_count': 3,
        'profile_filter': profile
    }).execute()
    
    return [item['content'] for item in result.data]

def get_user_data(user_id: str) -> dict:
    """Récupère les données utilisateur"""
    return supabase.table('users').select('*').eq('id', user_id).execute().data
