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
    layout="centered",
    initial_sidebar_state="expanded"
)

# Initialisation de session
if 'history' not in st.session_state:
    st.session_state.history = []
if 'profile' not in st.session_state:
    st.session_state.profile = None

# Sidebar pour l'upload vidéo
with st.sidebar:
    st.header("🎯 Configuration Initiale")
    with st.expander("ℹ️ Instructions", expanded=True):
        st.markdown("""
        1. Téléchargez votre vidéo pitch (max 50MB)
        2. Attendez la détection automatique du profil
        3. Dialoguez avec votre coach IA !
        """)
    
    uploaded_file = st.file_uploader("Choisir un fichier", 
                                   type=["mp4", "mov", "m4a", "mp3"],
                                   label_visibility="collapsed")
    
    if uploaded_file:
        try:
            # Vérification taille fichier
            MAX_SIZE = 50 * 1024 * 1024  # 50MB
            if uploaded_file.size > MAX_SIZE:
                raise ValueError(f"Taille maximale dépassée ({uploaded_file.size//(1024*1024)}MB > 50MB)")

            # Sauvegarde temporaire
            with tempfile.NamedTemporaryFile(delete=False, suffix=uploaded_file.name) as tmp_file:
                tmp_file.write(uploaded_file.getbuffer())
                tmp_file_path = tmp_file.name
                
            time.sleep(0.5)  # Synchronisation fichier
            
            # Conversion et transcription
            with st.status("🔍 Analyse en cours...", expanded=True) as status:
                st.write("Transcription audio...")
                transcription = transcribe_audio(tmp_file_path)
                
                # Configuration stockage
                bucket_name = "pitch-videos"
                
                # Vérification bucket
                try:
                    supabase.storage.get_bucket(bucket_name)
                except Exception as e:
                    status.error(f"""
                    **Configuration manquante :**  
                    Créez le bucket '{bucket_name}' dans Supabase avec :  
                    - Accès public ✅  
                    - Taille max : 50MB  
                    - MIME Types : video/*, audio/*
                    """)
                    raise
                
                # Upload sécurisé
                try:
                    st.write("Téléversement vers Supabase...")
                    unique_name = f"{int(time.time())}_{uploaded_file.name}"
                    res = supabase.storage.from_(bucket_name).upload(
                        path=unique_name,
                        file=tmp_file_path,
                        options={"content-type": uploaded_file.type}
                    )
                    
                    if not res:
                        raise ConnectionError("Échec silencieux de l'upload")
                        
                    video_url = supabase.storage.from_(bucket_name).get_public_url(unique_name)
                except Exception as e:
                    status.error(f"Échec upload : {str(e)}")
                    raise
                
                # Détection profil
                st.write("Analyse du profil DISC...")
                keywords = {
                    "rouge": {"décision": 2, "résultat": 3, "efficacité": 2},
                    "jaune": {"créativité": 3, "inspiration": 2, "vision": 2},
                    "vert": {"harmonie": 3, "équipe": 2, "collaboration": 2},
                    "bleu": {"analyse": 3, "méthode": 2, "logique": 2}
                }
                
                profile_scores = {}
                content = transcription.lower()
                for color, terms in keywords.items():
                    profile_scores[color] = sum(
                        content.count(term) * weight 
                        for term, weight in terms.items()
                    )
                
                st.session_state.profile = max(profile_scores, key=profile_scores.get)
                status.update(label="Analyse terminée !", state="complete", expanded=False)
            
            # Sauvegarde transactionnelle
            try:
                supabase.table("pitches").insert({
                    "transcription": transcription,
                    "profile": st.session_state.profile,
                    "video_name": uploaded_file.name,
                    "video_path": video_url
                }).execute()
            except Exception as e:
                supabase.storage.from_(bucket_name).remove([unique_name])  # Rollback
                raise

            # Affichage résultats
            col1, col2 = st.columns([1, 2])
            with col1:
                st.metric("Profil détecté", st.session_state.profile.capitalize())
            with col2:
                st.progress(profile_scores[st.session_state.profile]/10, 
                           text="Score de correspondance")

        except Exception as e:
            st.error(f"""
            **Échec du traitement**  
            {str(e)}  
            → Vérifiez le format du fichier  
            → Réduisez la durée de la vidéo  
            → Contactez le support si persistant
            """)

# Interface principale
st.title("🤖 Coach DISC 4Colors")
st.caption("Votre assistant personnel pour le développement professionnel")

# Affichage historique conversationnel
for msg in st.session_state.history:
    avatar = "🧑💻" if msg["role"] == "user" else "🤖"
    with st.chat_message(msg["role"], avatar=avatar):
        st.write(msg["content"])

# Gestion interaction
if prompt := st.chat_input("Parlez-moi de votre situation..."):
    st.session_state.history.append({"role": "user", "content": prompt})
    
    try:
        with st.spinner("🔎 Recherche de contextes pertinents..."):
            context = get_rag_context(prompt, st.session_state.profile)
        
        with st.spinner("💡 Génération de la réponse..."):
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
        st.error(f"🚨 Erreur : {str(e)}")
    
    st.rerun()

# Gestion profil manuel
with st.expander("⚙️ Personnalisation du Profil", expanded=False):
    cols = st.columns([3, 1])
    with cols[0]:
        new_profile = st.selectbox(
            "Modifier le profil détecté :",
            ["rouge", "jaune", "vert", "bleu"],
            index=["rouge", "jaune", "vert", "bleu"].index(st.session_state.profile) 
            if st.session_state.profile else 0,
            label_visibility="collapsed"
        )
    with cols[1]:
        if st.button("✅ Appliquer", use_container_width=True):
            st.session_state.profile = new_profile
            st.toast(f"Profil basculé en {new_profile.capitalize()} !")
