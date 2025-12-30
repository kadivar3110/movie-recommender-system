import streamlit as st 
import pandas as pd
import pickle as pkl
import requests
import os
import re
import string

# Define the preprocessing function expected by the pickle files
def preprocess_text(text):
    text = text.lower()
    text = re.sub(r'<.*?>', '', text)
    text = re.sub(f'[{re.escape(string.punctuation)}]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# Page configuration
st.set_page_config(
    page_title="🎬 Movie Recommender",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'page' not in st.session_state:
    st.session_state.page = 'home'
if 'selected_review_movie' not in st.session_state:
    st.session_state.selected_review_movie = None
if 'recommendations' not in st.session_state:
    st.session_state.recommendations = None
if 'current_selected_movie' not in st.session_state:
    st.session_state.current_selected_movie = None
if 'recommendations' not in st.session_state:
    st.session_state.recommendations = None
if 'current_selected_movie' not in st.session_state:
    st.session_state.current_selected_movie = None

# Custom CSS for better styling
st.markdown("""
    <style>
    .main-title {
        text-align: center;
        font-size: 3em;
        font-weight: bold;
        margin-bottom: 1rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .subtitle {
        text-align: center;
        font-size: 1.2em;
        color: #666;
        margin-bottom: 2rem;
    }
    .movie-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin: 10px 0;
    }
    .recommendation-title {
        font-size: 1.5em;
        font-weight: bold;
        margin: 20px 0 10px 0;
    }
    .meta-tag {
        background-color: #e9ecef;
        color: #000000;
        padding: 5px 10px;
        border-radius: 15px;
        font-size: 0.9em;
        margin-right: 5px;
        display: inline-block;
        margin-bottom: 5px;
    }
    .cast-name {
        font-weight: bold;
        color: #2c3e50;
    }
    .character-name {
        font-style: italic;
        color: #7f8c8d;
        font-size: 0.9em;
    }
    </style>
""", unsafe_allow_html=True)

# Load data
script_dir = os.path.dirname(os.path.abspath(__file__))
pkl_path = os.path.join(script_dir, 'movie_dict.pkl')
movie_dict = pkl.load(open(pkl_path, 'rb'))
movies = pd.DataFrame(movie_dict)

# Load Sentiment Analysis Models
def download_model_file(filename, repo_url="https://github.com/kadivar3110/movie-recommender-system/releases/download/v1"):
    """Download model file from GitHub release if it doesn't exist locally"""
    file_path = os.path.join(script_dir, filename)
    
    if os.path.exists(file_path):
        return file_path
    
    # Try to download from GitHub
    try:
        url = f"{repo_url}/{filename}"
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return file_path
    except Exception as e:
        st.error(f"Could not download {filename}: {e}")
        return None

try:
    # Try to load preprocessing.pkl, fallback to local function if it fails
    try:
        preprocess_pkl_path = download_model_file('preprocessing.pkl')
        if preprocess_pkl_path:
            preprocess_func = pkl.load(open(preprocess_pkl_path, 'rb'))
        else:
            preprocess_func = preprocess_text
    except:
        preprocess_func = preprocess_text

    # Download and load vectorizer
    vectorizer_path = download_model_file('vectorizer.pkl')
    if vectorizer_path:
        vectorizer = pkl.load(open(vectorizer_path, 'rb'))
    else:
        vectorizer = None

    # Download and load model
    model_path = download_model_file('model.pkl')
    if model_path:
        model = pkl.load(open(model_path, 'rb'))
    else:
        model = None
        
except Exception as e:
    st.error(f"Error loading sentiment models: {e}")
    preprocess_func = None
    vectorizer = None
    model = None

# TMDB API configuration
TMDB_API_KEY = 'cec0ac97e33607856fb591da0eaff05a'
TMDB_BEARER_TOKEN = 'eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJjZWMwYWM5N2UzMzYwNzg1NmZiNTkxZGEwZWFmZjA1YSIsIm5iZiI6MTc2MDI2ODY4MC43NzksInN1YiI6IjY4ZWI5MTg4ODkzY2UyZDdjMzMyMWQwZCIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.QLV0SbAcyCXScei0EgoEd_xexGKv18PhF7o8lSxKfJY'
TMDB_BASE_URL = 'https://api.themoviedb.org/3'
POSTER_BASE_URL = 'https://image.tmdb.org/t/p/w500'

@st.cache_data
def get_poster_url(movie_id):
    """Fetch poster URL from TMDB API using movie ID"""
    try:
        url = f'{TMDB_BASE_URL}/movie/{movie_id}?api_key={TMDB_API_KEY}'
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            poster_path = data.get('poster_path')
            if poster_path:
                return f'{POSTER_BASE_URL}{poster_path}'
    except Exception as e:
        pass
    return None

@st.cache_data
def get_movie_details(movie_id):
    """Fetch detailed movie info from TMDB API"""
    try:
        url = f'{TMDB_BASE_URL}/movie/{movie_id}?api_key={TMDB_API_KEY}'
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        pass
    return None

@st.cache_data
def get_movie_credits(movie_id):
    """Fetch movie credits (cast and crew) from TMDB API"""
    try:
        url = f'{TMDB_BASE_URL}/movie/{movie_id}/credits?api_key={TMDB_API_KEY}'
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        pass
    return None

@st.cache_data
def get_movie_reviews(movie_id):
    """Fetch reviews from TMDB API"""
    try:
        url = f'{TMDB_BASE_URL}/movie/{movie_id}/reviews'
        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {TMDB_BEARER_TOKEN}"
        }
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get('results', [])
    except Exception as e:
        st.error(f"Error fetching reviews: {e}")
    return []

# PAGE ROUTING
if st.session_state.page == 'review':
    # REVIEW PAGE - Show only this, nothing else
    st.markdown('<h1 class="main-title">📝 Movie Review</h1>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    if st.session_state.selected_review_movie:
        movie_title = st.session_state.selected_review_movie
        try:
            movie_idx = movies[movies['title'] == movie_title].index[0]
            movie_id = movies.iloc[movie_idx]['id']
            poster_url = get_poster_url(int(movie_id))
            movie_details = get_movie_details(int(movie_id))
            movie_credits = get_movie_credits(int(movie_id))
            
            col1, col2 = st.columns([1, 2])
            
            with col1:
                if poster_url:
                    st.image(poster_url, use_container_width=True)
                else:
                    st.info("📸 Poster not available")
            
            with col2:
                st.markdown(f"## {movie_title}")
                
                if movie_details:
                    # Tagline
                    tagline = movie_details.get('tagline', '')
                    if tagline:
                        st.markdown(f"*{tagline}*")
                    
                    st.markdown("### ℹ️ Details")
                    # Metadata with badges
                    release_date = movie_details.get('release_date', 'N/A')
                    rating = movie_details.get('vote_average', 'N/A')
                    runtime = movie_details.get('runtime', 'N/A')
                    lang = movie_details.get('original_language', 'N/A').upper()
                    
                    st.markdown(f"""
                        <div style="margin-bottom: 10px;">
                            <span class="meta-tag">📅 {release_date}</span>
                            <span class="meta-tag">⭐ {rating}/10</span>
                            <span class="meta-tag">⏱️ {runtime} min</span>
                            <span class="meta-tag">🗣️ {lang}</span>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    genres = movie_details.get('genres', [])
                    if genres:
                        genre_html = "".join([f'<span class="meta-tag" style="background-color: #e2e8f0;">{g["name"]}</span>' for g in genres])
                        st.markdown(f"**Genres:** {genre_html}", unsafe_allow_html=True)
                    
                    st.markdown("### 📖 Overview")
                    st.write(movie_details.get('overview', 'No overview available'))

            # Cast & Crew Section
            if movie_credits:
                st.markdown("---")
                st.subheader("🎭 Cast & Crew")
                
                # Director
                directors = [crew['name'] for crew in movie_credits.get('crew', []) if crew['job'] == 'Director']
                if directors:
                    st.markdown(f"**🎬 Director:** {', '.join(directors)}")
                
                # Top Cast in Columns
                cast = movie_credits.get('cast', [])
                if cast:
                    st.markdown("**🌟 Top Cast:**")
                    cols = st.columns(4)
                    for idx, actor in enumerate(cast[:4]):
                        with cols[idx]:
                            st.markdown(f"""
                                <div style="text-align: center; background-color: #f8f9fa; padding: 10px; border-radius: 10px;">
                                    <div class="cast-name">{actor['name']}</div>
                                    <div class="character-name">{actor['character']}</div>
                                </div>
                            """, unsafe_allow_html=True)
            
            st.markdown("---")
            st.subheader("💬 Movie Reviews (Sentiment Analysis)")
            
            reviews = get_movie_reviews(int(movie_id))
            
            if reviews:
                # Limit to at least 20 reviews if available, else take all
                display_reviews = reviews[:20] if len(reviews) >= 20 else reviews
                
                # Calculate Sentiment Stats
                positive_count = 0
                negative_count = 0
                analyzed_reviews = []

                # Pre-analyze to get stats
                for review in display_reviews:
                    content = review.get('content', '')
                    author = review.get('author', 'Anonymous')
                    sentiment = None
                    
                    if content and preprocess_func and vectorizer and model:
                        try:
                            processed_text = preprocess_func(content)
                            vectorized_text = vectorizer.transform([processed_text])
                            prediction = model.predict(vectorized_text)[0]
                            sentiment = prediction
                            if prediction == 1:
                                positive_count += 1
                            else:
                                negative_count += 1
                        except:
                            pass
                    
                    analyzed_reviews.append({
                        'author': author,
                        'content': content,
                        'sentiment': sentiment
                    })
                
                # Display Metrics
                m1, m2, m3 = st.columns(3)
                m1.metric("Total Reviews", len(display_reviews))
                m2.metric("Positive", positive_count, delta_color="normal")
                m3.metric("Negative", negative_count, delta_color="inverse")
                
                st.markdown("---")

                # Display Reviews
                for review in analyzed_reviews:
                    author = review['author']
                    content = review['content']
                    sentiment = review['sentiment']
                    
                    if sentiment == 1:
                        st.success(f"**{author}**: {content}") # Green for positive
                    elif sentiment == 0:
                        st.error(f"**{author}**: {content}")   # Red for negative
                    else:
                        st.info(f"**{author}**: {content}")    # Neutral/Unknown
                    
            else:
                st.info("No reviews found for this movie.")
            
            # Back button at the end of review page
            st.markdown("---")
            col1, col2, col3 = st.columns([1, 1, 1])
            with col2:
                if st.button("⬅️ Back to Home", use_container_width=True, key="back_btn_end"):
                    st.session_state.page = 'home'
                    st.rerun()

        except Exception as e:
            st.error(f"Error loading movie details: {e}")
    st.stop()  # Stop here, don't render home page

# HOME PAGE - RECOMMENDATIONS
st.markdown('<h1 class="main-title">🎬 Movie Recommendation Engine</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Discover your next favorite movie!</p>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("📋 Instructions")
    st.info("""
    1. 🎯 Select a movie from the dropdown
    2. 🔍 Click "Get Recommendations"
    3. 🎬 Browse personalized recommendations
    4. 📝 Click "Review" to see reviews
    """)
    st.write(f"**Total movies:** {len(movies)}")

# Main content
col1, col2, col3 = st.columns([3, 1, 1])

with col1:
    selected_movie = st.selectbox(
        label="🎬 Choose a movie:",
        options=movies['title'].values,
        help="Select any movie to get personalized recommendations",
        key="movie_select"
    )

with col2:
    st.write("")  # Vertical spacer
    
with col3:
    recommend_btn = st.button("🔍 Get Recommendations", use_container_width=True, key="recommend_btn")

if recommend_btn:
    st.session_state.current_selected_movie = selected_movie
    with st.spinner("⏳ Finding recommendations..."):
        similarity_path = os.path.join(script_dir, 'similarity.pkl')
        
        # Download similarity.pkl if it doesn't exist
        if not os.path.exists(similarity_path):
            url = "https://github.com/kadivar3110/movie-recommender-system/releases/download/v1/similarity.pkl"
            try:
                with st.spinner("Downloading similarity matrix (one-time setup)..."):
                    response = requests.get(url, stream=True)
                    response.raise_for_status()
                    with open(similarity_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
            except Exception as e:
                st.error(f"Error downloading similarity file: {e}")
                st.stop()

        similarity = pkl.load(open(similarity_path, 'rb'))

        def recommend(movie):
            movie_index = movies[movies['title'] == movie].index[0]
            distances = similarity[movie_index]
            return distances

        distances = recommend(selected_movie)
        movie_list = sorted(list(enumerate(distances)), reverse=True, key=lambda x: x[1])[1:6]
        st.session_state.recommendations = movie_list
        # Store distances too if needed, or just re-calculate/ignore score for now to keep it simple
        # Actually, let's store the distances or just the scores in the list
        # movie_list is [(index, score), ...] so we have the scores.

if st.session_state.recommendations and st.session_state.current_selected_movie:
    movie_list = st.session_state.recommendations
    current_movie = st.session_state.current_selected_movie
    
    # Display selected movie
    st.markdown("---")
    st.markdown('<p class="recommendation-title">📽️ You Selected</p>', unsafe_allow_html=True)
    
    input_movie_idx = movies[movies['title'] == current_movie].index[0]
    input_movie_id = movies.iloc[input_movie_idx]['id']
    input_poster_url = get_poster_url(int(input_movie_id))
    
    col1, col2 = st.columns([1, 2])
    with col1:
        if input_poster_url:
            st.image(input_poster_url, width=200)
        else:
            st.info("📸 Poster not available")
    with col2:
        st.markdown(f"### {current_movie}", unsafe_allow_html=True)
        st.success("✅ Ready to explore recommendations!")
    
    # Display recommended movies
    st.markdown("---")
    st.markdown('<p class="recommendation-title">⭐ Top 5 Recommendations</p>', unsafe_allow_html=True)
    
    rec_cols = st.columns(5)
    
    def go_to_review(movie_name):
        st.session_state.selected_review_movie = movie_name
        st.session_state.page = 'review'
    
    for idx, (i, col) in enumerate(zip(movie_list, rec_cols)):
        rec_movie_title = movies.iloc[i[0]].title
        rec_movie_id = movies.iloc[i[0]]['id']
        rec_poster_url = get_poster_url(int(rec_movie_id))
        similarity_score = i[1] # i is (index, score)
        
        with col:
            st.markdown(f"**#{idx + 1}**", unsafe_allow_html=True)
            if rec_poster_url:
                st.image(rec_poster_url, width=150)
            else:
                st.info("📸 Poster N/A")
            st.markdown(f"**{rec_movie_title}**")
            st.caption(f"Match: {similarity_score:.1%}")
            
            # Review button with callback
            st.button(
                "📝 Review", 
                key=f"review_btn_{idx}",
                on_click=go_to_review,
                args=(rec_movie_title,)
            )
    
    if recommend_btn:
        st.success("✨ Recommendations loaded successfully!")