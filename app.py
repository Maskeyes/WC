import streamlit as st
import pandas as pd
from PIL import Image, ExifTags
import os
import io

# --- Configuration ---
# Set page layout to wide for better use of screen space
st.set_page_config(layout="wide")

# Path configuration for deployment (case-sensitive on Render/Streamlit Cloud)
PHOTOS_FOLDER = 'photos'
CSV_FILE = 'profiles.csv'

# --- Utility Functions ---

# Use st.cache_data to load the CSV file once and cache the result. 
# This is crucial for fast and stable deployment on Render/Streamlit Cloud.
@st.cache_data
def load_data():
    """Loads profile data from CSV."""
    if not os.path.exists(CSV_FILE):
        st.error(f"Error: Required file '{CSV_FILE}' not found in the root directory.")
        return pd.DataFrame()
    
    try:
        data = pd.read_csv(CSV_FILE)
        return data
    except Exception as e:
        st.error(f"Error loading CSV data: {e}")
        return pd.DataFrame()

def get_image_path(filename):
    """
    Constructs a robust path to the image file, handling potential 
    case-sensitivity issues on Linux-based deployment servers (like Render).
    """
    # Use os.path.join for cross-OS compatibility
    path = os.path.join(PHOTOS_FOLDER, filename)
    
    # Check for exact match
    if os.path.exists(path):
        return path
    
    # Check for case-insensitive match (safer on deployment)
    try:
        folder_contents = os.listdir(PHOTOS_FOLDER)
        for content in folder_contents:
            if content.lower() == filename.lower():
                return os.path.join(PHOTOS_FOLDER, content)
    except FileNotFoundError:
        return None # Return None if photos folder is missing
        
    return None

def fix_image_orientation(img_path):
    """Opens image, fixes EXIF orientation, and returns PIL Image object."""
    try:
        img = Image.open(img_path)
        
        # Check for EXIF data
        if hasattr(img, '_getexif'):
            exif = img._getexif()
            if exif is not None:
                # Find the Orientation tag (274)
                for tag, value in exif.items():
                    if ExifTags.TAGS.get(tag) == 'Orientation':
                        if value == 3:
                            img = img.rotate(180, expand=True)
                        elif value == 6:
                            img = img.rotate(270, expand=True)
                        elif value == 8:
                            img = img.rotate(90, expand=True)
                        break
        return img
    except Exception:
        # If the file is not an image or is corrupted, return a placeholder
        # For simplicity, returning the path for a standard Streamlit error handling
        return img_path


# --- Custom HTML/CSS for Flippable Card and Pinterest Grid ---
def set_custom_css():
    """Injects custom CSS for the Pinterest grid and 3D flip card effect."""
    st.markdown("""
    <style>
    /* 1. Hide Streamlit Header, Footer, and Main Title/Count */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Hide the Streamlit H1 title and the "X profiles found" text which are 
       Streamlit's default elements for st.title and st.dataframe */
    .st-emotion-cache-18ni7ap { display: none !important; } /* Targets the main title/header container */
    
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
        box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);
        border-radius: 12px;
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
        justify-content: center;
        padding: 15px;
        box-sizing: border-box;
    }

    /* Front Side Styling */
    .flip-card-front {
        background-color: #ffffff; 
        color: black;
        border: 1px solid #e0e0e0;
        
    }
    
    /* Image sizing on the front */
    .flip-card-front img {
        width: 100%; /* Fill the container width */
        max-height: 250px; /* Fixed max height for consistency */
        object-fit: cover; /* Ensures image fills space without stretching */
        border-radius: 8px;
        margin-bottom: 10px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }

    /* Back Side Styling */
    .flip-card-back {
        background-color: #262730; /* Dark background for contrast */
        color: white;
        transform: rotateY(180deg);
        justify-content: flex-start; /* Start content from top */
        text-align: left;
        padding: 30px;
    }
    
    .flip-card-back h4 {
        margin-top: 15px;
        margin-bottom: 5px;
        font-weight: 600;
        color: #8c9096; /* Subtle heading color */
    }
    .flip-card-back p {
        margin: 0;
        font-size: 1.1rem;
        color: #ffffff;
    }
    
    /* Name on Front Card */
    .profile-name-front {
        font-size: 1.5rem;
        font-weight: bold;
        color: #007bff; /* Highlight name color */
        margin-top: 5px;
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
        st.header("🔎 Filter Profiles")
        
        # 1. Search Bar
        search_query = st.text_input("Search by Name or Details", "").lower()
        
        # 2. Country Filter
        all_countries = ['All'] + sorted(df['Country'].unique().tolist())
        selected_country = st.selectbox("Select Country", all_countries)
    
    # --- Filtering Logic ---
    filtered_df = df.copy()

    # Apply Country Filter
    if selected_country != 'All':
        filtered_df = filtered_df[filtered_df['Country'] == selected_country]

    # Apply Search Query Filter
    if search_query:
        # Search across all columns (Name, Birthday, Town/County, Country)
        search_mask = filtered_df.apply(lambda row: 
            search_query in ' '.join(row.astype(str).str.lower()), axis=1)
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
            photo_file = row['Photo File']
            birthday = row['Birthday']
            town = row['Town/County']
            country = row['Country']
            
            image_path = get_image_path(photo_file)
            
            # --- Build Card HTML ---
            
            # Start the flip-card container
            card_html = f"""
            <div class="flip-card">
              <div class="flip-card-inner">
                
                <!-- Front Side: Photo and Name -->
                <div class="flip-card-front">
                  <img src="data:image/png;base64," onerror="this.onerror=null; this.src='{image_path}';" alt="{name}">
                  <div class="profile-name-front">{name}</div>
                </div>
                
                <!-- Back Side: Details -->
                <div class="flip-card-back">
                  <h2 style="color: #007bff; margin-bottom: 20px;">{name}</h2>
                  
                  <h4>Birthday:</h4>
                  <p>{birthday}</p>
                  
                  <h4>Town/County:</h4>
                  <p>{town}</p>
                  
                  <h4>Country:</h4>
                  <p>{country}</p>
                </div>
                
              </div>
            </div>
            """
            
            # The image path handling is tricky in Streamlit/Render HTML 
            # We use an optimized way to display the image.
            
            img_to_render = fix_image_orientation(image_path)
            
            # Convert the PIL Image to base64 for direct embedding in the HTML
            buffered = io.BytesIO()
            img_to_render.save(buffered, format="PNG")
            img_str = f"data:image/png;base64,{st.image(img_to_render, use_column_width='auto')}"
            
            # Re-render the HTML template with the correct base64 data injected
            # Note: Streamlit's st.image is used to generate the base64 URL, 
            # and then we use the generated image data in the custom HTML structure.
            st.markdown(card_html.replace(f'<img src="data:image/png;base64,"', 
                                          f'<img src="{img_str}"'), 
                        unsafe_allow_html=True)

    # End the custom HTML container
    st.markdown('</div>', unsafe_allow_html=True)


if __name__ == '__main__':
    main()