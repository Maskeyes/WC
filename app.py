import streamlit as st
import pandas as pd
import os
import csv
from PIL import Image, ExifTags
import io
import base64

# --- Configuration ---
st.set_page_config(layout="wide")
CSV_FILE = 'profiles.csv'
PHOTOS_FOLDER = 'photos'

# --- Utility Functions ---

@st.cache_data
def load_data():
    """Loads the profile data from the CSV file and normalizes column names."""
    if not os.path.exists(CSV_FILE):
        st.error(f"Error: Required file '{CSV_FILE}' not found in the root directory.")
        return pd.DataFrame()
    
    try:
        # 1. Detect delimiter using csv.Sniffer
        with open(CSV_FILE, 'r', newline='', encoding='utf-8') as f:
            sample = f.read(1024)
            if not sample.strip():
                st.error(f"Error: The file '{CSV_FILE}' is empty.")
                return pd.DataFrame()
            
            dialect = csv.Sniffer().sniff(sample)
            
        # 2. Read the CSV using the detected delimiter
        df = pd.read_csv(CSV_FILE, sep=dialect.delimiter, encoding='utf-8')
    except Exception as e:
        st.error(f"Error loading CSV data: {e}")
        return pd.DataFrame()

    # Define the exact column names the app code expects
    required_cols_map = {
        'name': 'Name',
        'birthday': 'Birthday',
        'town/county': 'Town/County',
        'country': 'Country'
    }
    
    # Normalize column names in the DataFrame to handle inconsistent capitalization
    df.columns = [col.strip().replace('_', ' ') for col in df.columns]

    # Map existing columns to the required names (case-insensitive check)
    for lower_name, target_col in required_cols_map.items():
        found_col = None
        for col in df.columns:
            if col.lower() == lower_name:
                found_col = col
                break
            
        if found_col and found_col != target_col:
            df.rename(columns={found_col: target_col}, inplace=True)
        elif found_col is None:
            # Only raise an error if a critical column is missing
            st.error(f"Error: The required column '{target_col}' is missing from '{CSV_FILE}'.")
            return pd.DataFrame()

    df['Name'] = df['Name'].astype(str).fillna('Unknown Profile')
    return df

def get_image_path(name):
    """
    Finds the image file in the photos folder where the filename contains
    the first name of the profile (case-insensitive).
    """
    try:
        first_name = name.strip().split(' ')[0].lower()
        if not first_name:
            return None

        # Robust path handling for deployment
        photos_dir = os.path.join(os.getcwd(), PHOTOS_FOLDER)

        if not os.path.isdir(photos_dir):
             photos_dir = PHOTOS_FOLDER
             if not os.path.isdir(photos_dir):
                 return None

        for filename in os.listdir(photos_dir):
            normalized_filename = filename.lower()
            
            if first_name in normalized_filename:
                return os.path.join(photos_dir, filename)
                
    except Exception:
        # Ignore file system errors and return None
        pass
        
    return None

def get_base64_image(image_path):
    """Loads image, fixes EXIF orientation, and returns base64 string for HTML."""
    if not image_path or not os.path.exists(image_path):
        # Return a Base64 string for a placeholder image
        return 'https://placehold.co/300x400/CCCCCC/888888?text=No+Photo'

    try:
        img = Image.open(image_path)
        
        # --- FIX FOR EXIF ORIENTATION ---
        if hasattr(img, '_getexif'):
            exif = img._getexif()
            if exif is not None:
                for tag, value in exif.items():
                    if ExifTags.TAGS.get(tag) == 'Orientation':
                        if value == 3:
                            img = img.rotate(180, expand=True)
                        elif value == 6:
                            img = img.rotate(270, expand=True)
                        elif value == 8:
                            img = img.rotate(90, expand=True)
                        break

        # Convert PIL Image to Base64
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/png;base64,{img_str}"

    except Exception:
        # Fallback to placeholder image URL on error
        return 'https://placehold.co/300x400/CCCCCC/888888?text=Error+Loading'


# --- Custom HTML/CSS for Flippable Card and Pinterest Grid ---
def set_custom_css():
    """Injects custom CSS for the Pinterest grid and 3D flip card effect."""
    st.markdown("""
    <style>
    /* 1. Hide Streamlit Header, Footer, Title, and Count */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    /* Hide the default Streamlit title and header elements */
    .st-emotion-cache-18ni7ap, .st-emotion-cache-10oheav { display: none !important; } 
    
    /* 2. Pinterest-style Grid Layout (Flexbox) */
    .pinterest-grid {
        display: flex;
        flex-wrap: wrap;
        gap: 1.5rem; /* Space between cards */
        justify-content: center; /* Center the grid on the page */
    }

    /* 3. Flip Card Styles */
    .flip-card {
        background-color: transparent;
        width: 300px; /* Card size - set for a nice balance in the grid */
        height: 400px;
        perspective: 1000px; /* 3D effect */
        box-shadow: 0 8px 16px 0 rgba(0,0,0,0.2);
        border-radius: 12px;
        margin-bottom: 25px; /* Add extra spacing for grid effect */
    }

    .flip-card-inner {
        position: relative;
        width: 100%;
        height: 100%;
        text-align: center;
        transition: transform 0.8s;
        transform-style: preserve-3d;
        border-radius: 12px;
    }

    /* Flip the card on hover */
    .flip-card:hover .flip-card-inner {
        transform: rotateY(180deg);
    }

    .flip-card-front, .flip-card-back {
        position: absolute;
        width: 100%;
        height: 100%;
        -webkit-backface-visibility: hidden; /* Safari */
        backface-visibility: hidden;
        border-radius: 12px;
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 20px;
        box-sizing: border-box;
    }

    /* Front Side Styling */
    .flip-card-front {
        background-color: #ffffff; 
        color: black;
        justify-content: flex-start; /* Start content from top */
    }
    
    /* Image sizing on the front */
    .flip-card-front img {
        width: 100%; 
        height: 80%; /* Takes up most of the card height */
        object-fit: cover; 
        border-radius: 8px;
        margin-bottom: 10px;
    }

    /* Back Side Styling */
    .flip-card-back {
        background-color: #007bff; /* Use a bright color for contrast */
        color: white;
        transform: rotateY(180deg);
        justify-content: center; /* Center content vertically */
        text-align: center;
    }
    
    .flip-card-back h4 {
        margin-top: 15px;
        margin-bottom: 5px;
        font-weight: 400;
        color: #e0e0e0; /* Subtle heading color */
        font-size: 1.1rem;
    }
    .flip-card-back p {
        margin: 0;
        font-size: 1.2rem;
        font-weight: bold;
        color: #ffffff;
    }
    
    /* Name on Front Card */
    .profile-name-front {
        font-size: 1.6rem;
        font-weight: bold;
        color: #333; 
        margin-top: auto; /* Pushes name to the bottom */
    }
    
    </style>
    """, unsafe_allow_html=True)


# --- Main Application Logic ---

def main():
    """Main function to run the Streamlit application."""
    
    # Apply custom CSS for the flippable card and grid
    set_custom_css()
    
    df = load_data()
    
    if df.empty:
        return

    # --- Sidebar Filters ---
    with st.sidebar:
        st.header("🔎 Profile Filters")
        
        # 1. Search Bar
        search_query = st.text_input("Search by Name or Details", "").lower()
        
        # 2. Country Filter
        all_countries = ['All'] + sorted(df['Country'].unique().tolist())
        selected_country = st.selectbox("Filter by Country", all_countries)
    
    # --- Filtering Logic ---
    filtered_df = df.copy()

    # Apply Country Filter
    if selected_country != 'All':
        filtered_df = filtered_df[filtered_df['Country'] == selected_country]

    # Apply Search Query Filter
    if search_query:
        # Search across all relevant columns
        search_mask = filtered_df.apply(lambda row: 
            search_query in ' '.join([
                str(row['Name']), str(row['Birthday']), 
                str(row['Town/County']), str(row['Country'])
            ]).lower(), axis=1)
        filtered_df = filtered_df[search_mask]
        
    # --- Profile Card Rendering (Pinterest Grid) ---
    
    # Start the custom HTML container for the grid
    st.markdown('<div class="pinterest-grid">', unsafe_allow_html=True)
    
    if filtered_df.empty:
        st.markdown(f'<div style="width: 100%; text-align: center; padding: 50px;">'
                    f'<h2>🥺 No profiles match your criteria.</h2></div>', 
                    unsafe_allow_html=True)
        
    else:
        # Iterate over filtered profiles and render each as a flippable card
        for index, row in filtered_df.iterrows():
            name = row['Name']
            birthday = row['Birthday']
            town = row['Town/County']
            country = row['Country']
            
            # Use the person's Name to find the image path (Fixes KeyError)
            image_path = get_image_path(name)
            
            # Get the Base64 image string for direct HTML embedding
            img_src = get_base64_image(image_path)
            
            # --- Build Card HTML ---
            card_html = f"""
            <div class="flip-card">
              <div class="flip-card-inner">
                
                <!-- Front Side: Photo and Bold Name -->
                <div class="flip-card-front">
                  <img src="{img_src}" alt="{name}">
                  <div class="profile-name-front">{name}</div>
                </div>
                
                <!-- Back Side: Details -->
                <div class="flip-card-back">
                  <h2 style="margin-bottom: 25px; font-size: 2rem;">{name}</h2>
                  
                  <h4>Town/County:</h4>
                  <p>{town}</p>
                  
                  <h4>Country:</h4>
                  <p>{country}</p>

                  <h4>Birthday:</h4>
                  <p>{birthday}</p>
                </div>
                
              </div>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)

    # End the custom HTML container
    st.markdown('</div>', unsafe_allow_html=True)


if __name__ == '__main__':
    main()