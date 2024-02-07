from transformers import VisionEncoderDecoderModel, ViTImageProcessor, AutoTokenizer
import torch
from PIL import Image
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import streamlit as st
from streamlit import set_page_config
import io
from collections import Counter
from nltk.corpus import stopwords
import nltk
import os
from dotenv import load_dotenv
from utils import set_background


# Download stopwords from nltk
nltk.download('stopwords')


# Set page configuration
set_page_config(
    page_title="SightSync",
    page_icon="🎵",
    layout="centered",
)

# Set the background
set_background("./wallpaper/lights.jpg")

# Load environment variables from .env file
load_dotenv()

# Access the Spotify API credentials
SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")

# Check if the credentials are available
if not SPOTIPY_CLIENT_ID or not SPOTIPY_CLIENT_SECRET:
    raise ValueError("Please provide valid Spotify API credentials in the .env file.")


sp = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials(SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET))

model = VisionEncoderDecoderModel.from_pretrained("nlpconnect/vit-gpt2-image-captioning")
feature_extractor = ViTImageProcessor.from_pretrained("nlpconnect/vit-gpt2-image-captioning")
tokenizer = AutoTokenizer.from_pretrained("nlpconnect/vit-gpt2-image-captioning")

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)

max_length = 16
num_beams = 4
gen_kwargs = {"max_length": max_length, "num_beams": num_beams}

stop_words = set(stopwords.words('english'))

# Initialize keyword counter
keyword_counter = Counter()


def remove_stopwords(keywords):
    return [word for word in keywords if word.lower() not in stop_words]


def update_recommendations(selected_keyword=None):
    if selected_keyword:
        st.write(f"Updating recommendations based on keyword: **{selected_keyword}**")
        # Add your code here to call the Spotify API or perform any other relevant action based on the selected keyword
        try:
            # Get top song recommendations based on the selected keyword
            song_recommendations = get_top_song_recommendations(selected_keyword, num_recommendations=6)

            st.write("### Top 6 Song Recommendations:")
            display_song_recommendations(song_recommendations)
        except Exception as e:
            st.error(f"An unexpected error occurred during recommendation update: {str(e)}")


def get_top_song_recommendations(caption, num_recommendations=6, selected_keyword=None):
    try:
        results = sp.search(q=caption, type='track', limit=num_recommendations)

        recommendations = []

        for idx, track_info in enumerate(results['tracks']['items'][:num_recommendations]):
            track_name = track_info['name']
            artist_name = track_info['artists'][0]['name']
            song_url = track_info['external_urls']['spotify']

            keywords = remove_stopwords(caption.split())  # Remove stopwords
            recommendations.append({
                "name": f"{idx + 1}. {track_name} by {artist_name}",
                "url": song_url,
                "keywords": keywords
            })

            # Update keyword counter
            keyword_counter.update(keywords)

        # Filter recommendations based on the selected keyword
        if selected_keyword:
            recommendations = [rec for rec in recommendations if selected_keyword in rec['keywords']]

        return recommendations if recommendations else [{"name": "No recommendations found", "url": "", "keywords": []}]

    except Exception as e:
        st.error(f"Error fetching song recommendations: {str(e)}")
        return []


def generate_spotify_player_html(spotify_url):
    return f'<iframe src="https://open.spotify.com/embed/track/{spotify_url.split("/")[-1]}" ' \
           f'width="300" height="80" frameborder="0" allowtransparency="true" allow="encrypted-media"></iframe>'


def display_song_recommendations(song_recommendations):
    # Display the song recommendations in a grid layout
    col1, col2 = st.columns(2)

    for i, recommendation in enumerate(song_recommendations, 1):
        with col1 if i % 2 != 0 else col2:
            st.write(f"{recommendation['name']}")
            st.markdown(generate_spotify_player_html(recommendation['url']), unsafe_allow_html=True)


def predict_step(uploaded_file, selected_keyword=None):
    try:
        with io.BytesIO(uploaded_file.read()) as stream:
            i_image = Image.open(stream)
            if i_image.mode != "RGB":
                i_image = i_image.convert(mode="RGB")

            st.image(i_image, caption="Uploaded Image.", use_column_width=True)
            st.write("")

            # Display a loading spinner
            with st.spinner("Classifying..."):
                pixel_values = feature_extractor(images=[i_image], return_tensors="pt").pixel_values
                pixel_values = pixel_values.to(device)

                # Create attention mask to handle padding
                attention_mask = torch.ones_like(pixel_values[..., 0], dtype=torch.long, device=device)

                output_ids = model.generate(pixel_values, attention_mask=attention_mask, **gen_kwargs)

                preds = tokenizer.batch_decode(output_ids, skip_special_tokens=True)
                preds = [pred.strip() for pred in preds]

                # Get top song recommendations based on the generated caption
                for caption in preds:
                    song_recommendations = get_top_song_recommendations(caption, num_recommendations=6,
                                                                        selected_keyword=selected_keyword)
                    st.write(f"**Caption:** {caption}")
                    st.write("### Top 6 Song Recommendations:")
                    display_song_recommendations(song_recommendations)

    except FileNotFoundError:
        st.error("Error: The file was not found. Please make sure you selected a valid file.")
    except Image.DecompressionBombError:
        st.error("Error: The uploaded image is too large. Please upload an image with a smaller size.")
    except Exception as ex:
        st.error(f"An unexpected error occurred during image processing: {str(ex)}")


# Streamlit UI
st.title("Sight-Sync")

uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png", "gif"])

if uploaded_file is not None:
    try:
        # Run the initial prediction without a selected keyword
        predict_step(uploaded_file)

        # Display clickable buttons for keywords in two columns
        st.write("Click on a keyword to filter recommendations:")
        num_columns = 2  # You can adjust the number of columns based on your preference
        columns = st.columns(num_columns)

        # Keep track of the number of displayed buttons
        buttons_displayed = 0

        for keyword, count in keyword_counter.items():
            if count > 1 and buttons_displayed < 4:
                # Choose the appropriate column for each keyword
                column_index = hash(keyword) % num_columns
                button_column = columns[column_index]

                # Add a button to the chosen column
                if button_column.button(keyword):
                    # Update recommendations based on the selected keyword
                    update_recommendations(selected_keyword=keyword)

                # Increment the count of displayed buttons
                buttons_displayed += 1

    except FileNotFoundError:
        st.error("Error: The file was not found. Please make sure you selected a valid file.")
    except Exception as ex:
        st.error(f"An unexpected error occurred: {str(ex)}")