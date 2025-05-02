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

# Initialisation de session
if 'history' not in st.session_state:
    st.session_state.history = []
if 'profile' not in st.session_state:
    st.session_state.profile = None
if 'uploaded_file' not in st.session_state:
    st.session_state.uploaded_file = None

# Sidebar pour l'upload video
with st.sidebar:
    st.header("🎯 Configuration Initiale")
    with st.expander("ℹ️ Instructions", expanded=True):
        st.markdown("""
        **Optimisez votre pitch en 3 étapes :**
        1. Téléchargez votre video (max 1GB)
        2. Analyse automatique du profil DISC
        3. Coaching personnalisé en temps réel
        """)
    
    uploaded_file = st.file_uploader(
        "Choisir un fichier", 
        type=["mp4", "mov", "m4a", "wav", "flac", "mp3"],
        label_visibility="collapsed",
        help="Formats supportés : Video/Audio (MP4, MOV, MP3, WAV, FLAC)"
    )
    
    if uploaded_file:
        st.session_state.uploaded_file = uploaded_file

# Traitement principal
if st.session_state.uploaded_file:
    try:
        uploaded_file = st.session_state.uploaded_file
        MAX_SIZE_GB = 1  # 1GB
        MAX_SIZE_BYTES = MAX_SIZE_GB * 1024 * 1024 * 1024
        
        if uploaded_file.size > MAX_SIZE_BYTES:
            raise ValueError(
                f"Taille maximale dépassée ({uploaded_file.size/(1024*1024):.1f}MB > {MAX_SIZE_GB*1024}MB)"
            )

        # Sauvegarde temporaire
        with tempfile.NamedTemporaryFile(delete=False, suffix=uploaded_file.name) as tmp_file:
            tmp_file.write(uploaded_file.getbuffer())
            tmp_file_path = tmp_file.name
            
        # Transcription audio
        with st.status("🔍 Analyse en cours...", expanded=True) as status:
            st.write("🚦 Démarrage du traitement...")
            
            # Vérification bucket
            bucket_name = "pitch-video"
            try:
                supabase.storage.get_bucket(bucket_name)
            except Exception as e:
                status.error(f"""
                **Configuration manquante :**  
                1. Créez le bucket '{bucket_name}' dans Supabase  
                2. Paramètres requis :  
                   - Accès public ✅  
                   - Taille max : {MAX_SIZE_GB}GB  
                   - MIME Types : video/*, audio/*
                """)
                raise RuntimeError("Bucket non configuré")
            
            # Upload sécurisé
            try:
                st.write("📤 Téléversement vers le cloud...")
                unique_name = f"{int(time.time())}_{uploaded_file.name}"
                res = supabase.storage.from_(bucket_name).upload(
                    path=unique_name,
                    file=uploaded_file.getvalue(),
                    file_options={"content-type": uploaded_file.type}
                )
                
                if 'error' in res:
                    raise ConnectionError(res['error'])
                    
                video_url = supabase.storage.from_(bucket_name).get_public_url(unique_name)
            except Exception as e:
                status.error(f"❌ Échec de l'upload : {str(e)}")
                raise
            
            # Transcription et analyse
            st.write("🎤 Transcription audio...")
            transcription = transcribe_audio(tmp_file_path)
            
            # Détection profil DISC (version corrigée)
            st.write("🧠 Analyse du profil...")
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
                    "duration": "00:00:00"  # À implémenter avec moviepy
                },
                "video_url": video_url
            }).execute()
            
            status.update(label="✅ Analyse terminée !", state="complete", expanded=False)

        # Affichage résultats
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.subheader(f"Profil détecté : **{st.session_state.profile.capitalize()}**")
            max_score = max(profile_scores.values())
            score_percent = (profile_scores[st.session_state.profile]/max_score) if max_score > 0 else 0
            st.progress(
                value=score_percent,
                text=f"Score de correspondance : {profile_scores[st.session_state.profile]} points"
            )

    except Exception as e:
        st.error(f"""
        ## Échec du traitement
        **Message d'erreur :**  
        {str(e)}  
        
        **Solutions possibles :**  
        - Vérifiez le format du fichier (MP4, MOV, MP3)  
        - Réduisez la durée sous 10 minutes  
        - Contactez le support : support@genup2050.com
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
        
        # Sauvegarde conversation
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
    
    cols = st.columns([3, 1])
    with cols[0]:
        new_profile = st.selectbox(
            "Sélectionnez un profil :",
            options=["rouge", "jaune", "vert", "bleu"],
            index=["rouge", "jaune", "vert", "bleu"].index(st.session_state.profile) if st.session_state.profile else 0,
            label_visibility="collapsed"
        )
    with cols[1]:
        if st.button("🔄 Appliquer", use_container_width=True):
            st.session_state.profile = new_profile
            st.toast(f"Profil basculé en **{new_profile.capitalize()}** !", icon="✅")
    
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
    feedback = st.text_area("Vos suggestions nous intéressent !", key="feedback_input")
    if st.button("Envoyer mon feedback", key="feedback_btn"):
        if feedback:
            supabase.table("feedbacks").insert({
                "content": feedback,
                "profile": st.session_state.profile
            }).execute()
            st.success("Merci pour votre contribution ! ✨")
            st.session_state.feedback_input = ""  # Réinitialiser le champ
        else:
            st.warning("Veuillez saisir un message avant d'envoyer")
