import streamlit as st
import pandas as pd
import os
import csv 
from PIL import Image

# Configuration
CSV_FILE = 'profiles.csv'
PHOTOS_FOLDER = 'photos'

# Ensure the page config is set for a good starting layout
st.set_page_config(layout="wide", page_title="Team Profiles")

@st.cache_data # CRITICAL FIX: Cache the data load to prevent repeated file access and redirection loops
def load_data():
    """Loads the profile data from the CSV file, attempting to detect the correct delimiter and standardizing country names."""
    try:
        if not os.path.exists(CSV_FILE):
             st.error(f"Error: The required file '{CSV_FILE}' was not found.")
             return pd.DataFrame()
             
        # 1. First, attempt to detect the delimiter
        dialect = None
        with open(CSV_FILE, 'r', newline='\n', encoding='utf-8') as f: # Use '\n' for robustness
            sample = f.read(1024)
            if not sample:
                st.error(f"Error: The file '{CSV_FILE}' is empty.")
                return pd.DataFrame()
            
            if sample.strip():
                dialect = csv.Sniffer().sniff(sample)
            else:
                dialect = csv.excel()
                
        # 2. Read the CSV using the detected delimiter
        df = pd.read_csv(CSV_FILE, sep=dialect.delimiter, encoding='utf-8')
        
        # Ensure required columns are present and fix case
        required_cols_map = {
            'Name': 'Name', 
            'Birthday': 'Birthday', 
            'Town/County': 'Town/County', 
            'Country': 'Country'
        }
        
        # Normalize column names in the DataFrame to handle inconsistent capitalization
        df.columns = [col.strip().replace('_', ' ') for col in df.columns]

        for required_col, target_col in required_cols_map.items():
            found_col = None
            for col in df.columns:
                if col.lower() == required_col.lower():
                    found_col = col
                    break
                
            if found_col and found_col != target_col:
                df.rename(columns={found_col: target_col}, inplace=True)
            elif found_col is None:
                st.error(f"Error: The required column '{required_col}' is missing from '{CSV_FILE}'.")
                st.info("Please ensure your CSV file has columns for 'Name', 'Birthday', 'Town/County', and 'Country'.")
                return pd.DataFrame()

        # Final check to ensure all target columns exist after normalization
        if not all(col in df.columns for col in required_cols_map.values()):
             return pd.DataFrame()

        # --- CRITICAL FIX: Country Data Cleaning for Unique Filters ---
        if 'Country' in df.columns:
            # 1. Strip whitespace
            df['Country'] = df['Country'].astype(str).str.strip()
            # 2. Apply Title case (e.g., 'united kingdom' -> 'United Kingdom')
            df['Country'] = df['Country'].str.title() 

        # Convert Name to string and fill NaNs
        df['Name'] = df['Name'].astype(str).fillna('Unknown Profile')
        return df
    except FileNotFoundError:
        st.error(f"Error: The file '{CSV_FILE}' was not found. Please place it in the application directory.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"An unexpected error occurred while loading the CSV: {e}")
        st.warning("Please ensure your file is a standard CSV (Comma delimited) with correct headers.")
        return pd.DataFrame()

def get_image_path(name):
    """
    Finds the image file in the photos folder where the filename contains
    the first name of the profile.
    """
    try:
        first_name = name.strip().split(' ')[0].lower()
        if not first_name:
            return None 

        # Check if the PHOTOS_FOLDER exists in the current environment
        photos_dir = PHOTOS_FOLDER
        if not os.path.isdir(photos_dir):
            return None 

        for filename in os.listdir(photos_dir):
            normalized_filename = filename.lower()
            
            # Check if the extracted first name is contained anywhere in the filename
            if first_name in normalized_filename:
                return os.path.join(PHOTOS_FOLDER, filename)
                
    except Exception:
        # Ignore file system errors
        pass
        
    return None

def display_profile_card(row):
    """
    Displays a single profile card with Streamlit components, 
    with larger fonts for detail fields.
    """
    image_path = get_image_path(row['Name'])

    # Create the main card container
    with st.container(border=True):
        
        # --- Image (Centered) ---
        # Use three columns to push the image to the center of the card container
        col_left, col_img, col_right = st.columns([0.5, 3, 0.5])
        
        with col_img:
            image_width = 200 # Size for prominence
            
            img_loaded = False
            if image_path and os.path.exists(image_path):
                try:
                    img = Image.open(image_path)
                    
                    # *** FIX FOR EXIF ORIENTATION (Preserving user's original logic) ***
                    exif_data = img.getexif()
                    if exif_data is not None:
                        orientation = exif_data.get(0x0112)
                        
                        if orientation == 3:
                            img = img.transpose(Image.ROTATE_180)
                        elif orientation == 6:
                            img = img.transpose(Image.ROTATE_270)
                        elif orientation == 8:
                            img = img.transpose(Image.ROTATE_90)
                            
                    st.image(img, width=image_width) 
                    img_loaded = True
                except Exception:
                    # Fallback for image loading issues
                    pass
            
            if not img_loaded:
                # Placeholder image
                st.image("https://placehold.co/200x250/CCCCCC/888888?text=No+Photo", width=image_width)

        # --- Details (Beneath the photo, centered, with bigger fonts) ---
        
        # Center the text using CSS in Markdown and reduce margin-top 
        st.markdown("<div style='text-align: center; margin-top: -15px;'>", unsafe_allow_html=True) 
        
        # Name (Keep current size 1.4em)
        st.markdown(f"**<span style='font-size: 1.4em;'>{row['Name']}</span>**", unsafe_allow_html=True)
        
        # Country (Bigger font: 1.2em)
        st.markdown(f"**<span style='font-size: 1.2em;'>{row.get('Country', 'N/A')}</span>**", unsafe_allow_html=True)

        # Birthday (with Cake emoji - Bigger font: 1.2em)
        st.markdown(f"<div style='font-size: 1.2em; color: #333; margin-top: 5px;'>🎂 {row.get('Birthday', 'N/A')}</div>", unsafe_allow_html=True)
        
        # Town/County (with House emoji - Bigger font: 1.2em)
        st.markdown(f"<div style='font-size: 1.2em; color: #333;'>🏠 {row.get('Town/County', 'N/A')}</div>", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)


def main():
    """Main function to run the Streamlit application."""
    
    df = load_data()

    if df.empty:
        st.stop() # Stop if data loading failed

    # --- Filtering Sidebar ---
    st.sidebar.header("Find Profiles")

    # Name Search (case-insensitive partial match)
    search_query = st.sidebar.text_input("Search by Name", "")

    # Country Filter (Unique countries from cleaned data)
    # The cleaning in load_data ensures this list is unique.
    all_countries = ['All'] + sorted(df['Country'].unique().tolist())
    country_select = st.sidebar.selectbox("Filter by Country", all_countries)
    
    # --- Apply Filters ---
    filtered_df = df.copy()

    # 1. Apply Name Filter
    if search_query:
        filtered_df = filtered_df[
            filtered_df['Name'].str.contains(search_query, case=False, na=False)
        ]

    # 2. Apply Country Filter
    if country_select != 'All':
        filtered_df = filtered_df[filtered_df['Country'] == country_select]

    # Removed: The title and the profile count header

    # --- Grid Layout ---
    
    if filtered_df.empty:
        st.warning("No profiles match your search criteria.")
        return # Stop execution if no results

    # Define the number of columns for the grid
    NUM_COLUMNS = 3
    
    # Iterate through the filtered DataFrame and display cards in a grid
    cols = st.columns(NUM_COLUMNS)
    col_index = 0

    for index, row in filtered_df.iterrows():
        with cols[col_index]:
            display_profile_card(row)
            st.markdown("<br>", unsafe_allow_html=True) 
            
        col_index = (col_index + 1) % NUM_COLUMNS
            
    st.markdown("<br><br>", unsafe_allow_html=True) 


if __name__ == '__main__':
    main()