import streamlit as st
import tempfile
import time
from supabase_client import supabase, get_rag_context
from rag_utils import generate_coaching_response
from whisper_utils import transcribe_audio

# Configuration de la page
st.set_page_config(
    page_title="Coach DISC 4Colors - GENUP2050",
    page_icon="🌟",
    layout="centered"
)

# Initialisation de session
if 'history' not in st.session_state:
    st.session_state.history = []
if 'profile' not in st.session_state:
    st.session_state.profile = None

# Sidebar pour l'upload vidéo
with st.sidebar:
    st.header("Configuration initiale")
    uploaded_file = st.file_uploader("🎥 Téléchargez votre pitch vidéo", 
                                   type=["mp4", "mov", "m4a", "mp3"])
    
    if uploaded_file:
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=uploaded_file.name) as tmp_file:
                tmp_file.write(uploaded_file.read())
                tmp_file_path = tmp_file.name
                
            time.sleep(0.5)  # Attente sécurisée
            
            # Conversion et transcription
            st.toast("Traitement du fichier...", icon="⏳")
            transcription = transcribe_audio(tmp_file_path)
            
            # Upload vers Supabase Storage
            bucket_name = "pitch-videos"
            supabase.storage.from_(bucket_name).upload(
                path=uploaded_file.name,
                file=tmp_file_path
            )
            video_url = supabase.storage.from_(bucket_name).get_public_url(uploaded_file.name)
            
            # Détection du profil DISC
            keywords = {
                "rouge": ["décision", "résultat", "efficacité"],
                "jaune": ["créativité", "inspiration", "vision"],
                "vert": ["harmonie", "équipe", "collaboration"],
                "bleu": ["analyse", "méthode", "logique"]
            }
            profile_scores = {color: sum(1 for term in terms if term in transcription.lower()) 
                             for color, terms in keywords.items()}
            st.session_state.profile = max(profile_scores, key=profile_scores.get)
            
            # Sauvegarde dans la table pitches
            supabase.table("pitches").insert({
                "transcription": transcription,
                "profile": st.session_state.profile,
                "video_name": uploaded_file.name,
                "video_path": video_url
            }).execute()
            
            st.success(f"Profil {st.session_state.profile.capitalize()} détecté !")

        except Exception as e:
            st.error(f"""
            **Erreur de traitement :**  
            {str(e)}  
            Vérifiez le format (MP4/MOV/MP3 <25MB)
            """)

# Interface principale
st.title("🌟 Coach DISC 4Colors - GENUP2050")
st.caption("Votre assistant IA pour le développement professionnel")

# Affichage historique
for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Gestion interaction
if prompt := st.chat_input("Parlez-moi de votre situation..."):
    st.session_state.history.append({"role": "user", "content": prompt})
    
    try:
        context = get_rag_context(prompt, st.session_state.profile)
        
        with st.spinner("Julia analyse votre situation..."):
            response = generate_coaching_response(
                prompt=prompt,
                context=context,
                profile=st.session_state.profile
            )
            
        st.session_state.history.append({"role": "assistant", "content": response})
        
        # Sauvegarde conversation
        supabase.table("conversations").insert({
            "profile": st.session_state.profile,
            "question": prompt,
            "reponse": response,
            "contexte": context
        }).execute()
        
    except Exception as e:
        st.error(f"Erreur de génération : {str(e)}")
    
    st.rerun()

# Gestion profil manuel
with st.expander("🔧 Modifier le profil DISC"):
    new_profile = st.selectbox(
        "Choisir un nouveau profil :",
        ["rouge", "jaune", "vert", "bleu"],
        index=["rouge", "jaune", "vert", "bleu"].index(st.session_state.profile) 
        if st.session_state.profile else 0
    )
    
    if st.button("Confirmer le changement"):
        st.session_state.profile = new_profile
        st.success(f"Profil basculé en {new_profile.capitalize()} !")
