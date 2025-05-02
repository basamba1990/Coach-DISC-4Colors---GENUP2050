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
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://genup2050.com/support',
        'Report a bug': "https://genup2050.com/bug",
        'About': "# Écosystème 4Colors - Transformez vos compétences !"
    }
)

# Vérification initiale du bucket
try:
    supabase.storage.get_bucket("pitch-videos")
except Exception as e:
    st.error(f"""
    ## Configuration requise 🔧
    1. Créez un bucket 'pitch-videos' dans Supabase
    2. Paramètres obligatoires :
       - Accès public ✅  
       - Taille max : 1GB  
       - MIME Types : video/*, audio/*
    """)
    st.stop()

# Initialisation de session
if 'history' not in st.session_state:
    st.session_state.update({
        'history': [],
        'profile': None,
        'uploaded_file': None,
        'feedback_input': ""
    })

# Sidebar pour l'upload vidéo
with st.sidebar:
    st.header("🎯 Configuration Initiale")
    with st.expander("ℹ️ Instructions", expanded=True):
        st.markdown("""
        **Optimisez votre pitch en 3 étapes :**
        1. Téléchargez votre vidéo (max 1GB)
        2. Analyse automatique du profil DISC
        3. Coaching personnalisé en temps réel
        """)
    
    uploaded_file = st.file_uploader(
        "Choisir un fichier", 
        type=["mp4", "mov", "m4a", "wav", "flac", "mp3"],
        label_visibility="collapsed",
        help="Formats supportés : Vidéo/Audio (MP4, MOV, MP3, WAV, FLAC)"
    )
    
    if uploaded_file:
        st.session_state.uploaded_file = uploaded_file

# Traitement principal
if st.session_state.uploaded_file:
    try:
        uploaded_file = st.session_state.uploaded_file
        MAX_SIZE_GB = 1
        MAX_SIZE_BYTES = MAX_SIZE_GB * 1024**3
        
        if uploaded_file.size > MAX_SIZE_BYTES:
            raise ValueError(
                f"Taille maximale dépassée ({uploaded_file.size/1024**2:.1f}MB > {MAX_SIZE_GB*1024}MB)"
            )

        with tempfile.NamedTemporaryFile(delete=False, suffix=uploaded_file.name) as tmp_file:
            tmp_file.write(uploaded_file.getbuffer())
            tmp_file_path = tmp_file.name
            
        with st.status("🔍 Analyse en cours...", expanded=True) as status:
            # Upload sécurisé
            try:
                st.write("📤 Téléversement vers Supabase...")
                unique_name = f"{int(time.time())}_{uploaded_file.name}"
                res = supabase.storage.from_("pitch-videos").upload(
                    path=unique_name,
                    file=uploaded_file.getvalue(),
                    file_options={
                        "content-type": uploaded_file.type,
                        "cache-control": "max-age=3600"
                    }
                )
                
                if res.get('error'):
                    raise ConnectionError(res['message'])
                    
                video_url = supabase.storage.from_("pitch-videos").get_public_url(unique_name)
            except Exception as e:
                status.error(f"❌ Échec de l'upload : {str(e)}")
                raise
            
            # Transcription et analyse
            st.write("🎤 Transcription audio...")
            transcription = transcribe_audio(tmp_file_path)
            
            st.write("🧠 Analyse du profil DISC...")
            keywords = {
                "rouge": ["décision", "résultat", "action", "défi"],
                "jaune": ["créativité", "inspiration", "vision", "enthousiasme"],
                "vert": ["harmonie", "équipe", "collaboration", "empathie"],
                "bleu": ["analyse", "méthode", "logique", "précision"]
            }
            
            content = transcription.lower()
            profile_scores = {
                color: sum(content.count(term) for term in terms)
                for color, terms in keywords.items()
            }
            st.session_state.profile = max(profile_scores, key=profile_scores.get)
            
            # Sauvegarde des données
            supabase.table("pitches").insert({
                "transcription": transcription,
                "profile": st.session_state.profile,
                "metadata": {
                    "file_name": uploaded_file.name,
                    "file_size": uploaded_file.size,
                    "duration": "00:00:00"
                },
                "video_url": video_url
            }).execute()
            
            status.update(label="✅ Analyse terminée !", state="complete", expanded=False)

        # Affichage résultats
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.subheader(f"Profil détecté : **{st.session_state.profile.capitalize()}**")
            max_score = max(profile_scores.values()) or 1
            st.progress(
                value=profile_scores[st.session_state.profile]/max_score,
                text=f"Score : {profile_scores[st.session_state.profile]}/{max_score}"
            )

    except Exception as e:
        st.error(f"""
        ## Échec du traitement
        **Erreur :** {str(e)}
        **Solutions :**
        - Format fichier valide (MP4, MOV, MP3)
        - Durée < 10 minutes
        - Contact : support@genup2050.com
        """)
        st.session_state.uploaded_file = None

# Interface principale
st.title("🤖 Coach DISC 4Colors")
st.caption("Votre assistant personnel pour le développement professionnel")

# Gestion de la conversation
for msg in st.session_state.history:
    with st.chat_message(msg["role"], avatar="🧑💻" if msg["role"] == "user" else "🤖"):
        st.write(msg["content"])

# Interaction utilisateur
if prompt := st.chat_input("Comment puis-je vous aider aujourd'hui ?"):
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
        
        supabase.table("conversations").insert({
            "profile": st.session_state.profile,
            "interaction": {
                "question": prompt,
                "reponse": response,
                "contexte": context
            }
        }).execute()
        
    except Exception as e:
        st.error(f"🚨 Erreur : {str(e)}")
    
    st.rerun()

# Personnalisation avancée
with st.expander("⚙️ Personnalisation du Profil", expanded=False):
    st.markdown("### Ajustement manuel du profil")
    
    current_profile = st.session_state.profile or "rouge"
    new_profile = st.selectbox(
        "Sélectionnez un profil :",
        options=["rouge", "jaune", "vert", "bleu"],
        index=["rouge", "jaune", "vert", "bleu"].index(current_profile),
        label_visibility="collapsed"
    )
    
    if st.button("🔄 Appliquer", key="profile_apply"):
        st.session_state.profile = new_profile
        st.toast(f"Profil basculé en {new_profile.capitalize()} !", icon="✅")
    
    st.markdown("---")
    st.markdown("""
    **Guide des profils :**
    - 🔴 **Rouge** : Leadership, action, résultats  
    - 🟡 **Jaune** : Créativité, vision, communication  
    - 🟢 **Vert** : Collaboration, empathie, harmonie  
    - 🔵 **Bleu** : Analyse, précision, méthodologie
    """)

# Section feedback
st.markdown("---")
with st.container():
    st.markdown("#### 📬 Feedback & Support")
    feedback = st.text_area("Vos suggestions nous intéressent !", 
                          value=st.session_state.feedback_input,
                          key="feedback")
    
    if st.button("Envoyer", key="feedback_btn"):
        if feedback.strip():
            supabase.table("feedbacks").insert({
                "content": feedback,
                "profile": st.session_state.profile
            }).execute()
            st.success("Merci pour votre contribution ! ✨")
            st.session_state.feedback_input = ""
        else:
            st.warning("Veuillez saisir un message valide")
