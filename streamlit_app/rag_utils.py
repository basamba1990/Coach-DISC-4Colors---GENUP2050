from openai import OpenAI
import streamlit as st

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def generate_coaching_response(prompt: str, context: list, profile: str) -> str:
    """Génère une réponse adaptée au profil DISC"""
    tone_instructions = {
        "rouge": "Réponses concises orientées action",
        "jaune": "Ton enthousiaste avec métaphores inspirantes",
        "vert": "Approche empathique et collaborative", 
        "bleu": "Structure logique avec données tangibles"
    }
    
    system_prompt = f"""
    Tu es Julia, coach expert en profils DISC 4Colors. 
    Style requis : {tone_instructions[profile]}
    Contexte utile : {context}
    """
    
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7 if profile == "jaune" else 0.4
    )
    return response.choices[0].message.content
