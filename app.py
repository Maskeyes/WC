import streamlit as st
import pandas as pd
import os
import csv
from PIL import Image, ExifTags
import io
import base64

# --- Configuration ---
# Set page layout to wide for better use of screen space
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
            
            # Use a slightly more lenient sniffer approach
            dialect = csv.Sniffer().sniff(sample) if sample.strip() else csv.excel()
            
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
        photos_dir = PHOTOS_FOLDER
        
        if not os.path.isdir(photos_dir):
             return None

        for filename in os.listdir(photos_dir):
            normalized_filename = filename.lower()
            
            if first_name in normalized_filename:
                # Return the full path relative to the app root
                return os.path.join(PHOTOS_FOLDER, filename)
                
    except Exception:
        pass
        
    return None

def get_base64_image_src(image_path):
    """
    Loads image, fixes EXIF orientation, and returns a data URL (base64 string) 
    for direct embedding into HTML.
    """
    placeholder_url = 'https://placehold.co/300x400/CCCCCC/888888?text=No+Photo'

    if not image_path or not os.path.exists(image_path):
        return placeholder_url

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

        # Convert PIL Image to Base64 (using PNG format for wide compatibility)
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/png;base64,{img_str}"

    except Exception:
        return placeholder_url


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
    
    /* 2. Pinterest-style Masonry Grid Layout (using column layout) */
    .pinterest-grid {
        column-count: 4; /* Default to 4 columns for large screens */
        column-gap: 1.5rem; /* Space between columns */
        width: 100%;
        max-width: 1200px; /* Limit width for aesthetics */
        margin: 0 auto;
    }
    
    /* Responsive adjustments for smaller screens */
    @media (max-width: 1024px) {
        .pinterest-grid {
            column-count: 3;
        }
    }
    @media (max-width: 768px) {
        .pinterest-grid {
            column-count: 2;
        }
    }
    @media (max-width: 480px) {
        .pinterest-grid {
            column-count: 1; /* Single column on small mobile screens */
        }
    }

    /* Cards must not break across columns */
    .flip-card {
        -webkit-column-break-inside: avoid;
        page-break-inside: avoid;
        break-inside: avoid;
        
        background-color: transparent;
        width: 100%; /* Take full width of the column */
        height: 400px; /* Fixed height for visual consistency */
        perspective: 1000px; 
        box-shadow: 0 8px 16px 0 rgba(0,0,0,0.2);
        border-radius: 12px;
        margin-bottom: 25px; /* Spacing between cards in the column */
    }

    /* 3. Flip Card Styles */
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
        -webkit-backface-visibility: hidden; 
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
        justify-content: flex-start;
    }
    
    /* Image sizing on the front */
    .flip-card-front img {
        width: 100%; 
        height: 80%; 
        object-fit: cover; 
        border-radius: 8px;
        margin-bottom: 10px;
    }

    /* Back Side Styling */
    .flip-card-back {
        background-color: #007bff; 
        color: white;
        transform: rotateY(180deg);
        justify-content: center; 
        text-align: center;
    }
    
    .flip-card-back h4 {
        margin-top: 15px;
        margin-bottom: 5px;
        font-weight: 400;
        color: #e0e0e0;
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
        margin-top: auto;
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
        search_mask = filtered_df.apply(lambda row: 
            search_query in ' '.join([
                str(row['Name']), str(row['Birthday']), 
                str(row['Town/County']), str(row['Country'])
            ]).lower(), axis=1)
        filtered_df = filtered_df[search_mask]
        
    # --- Profile Card Rendering (Pinterest Grid) ---
    
    # Start the custom HTML container for the Masonry grid
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
            
            image_path = get_image_path(name)
            img_src = get_base64_image_src(image_path)
            
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
            # Render the complete, self-contained HTML block
            st.markdown(card_html, unsafe_allow_html=True)

    # End the custom HTML container
    st.markdown('</div>', unsafe_allow_html=True)


if __name__ == '__main__':
    main()