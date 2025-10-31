import streamlit as st
import pandas as pd
import os
import csv 
from PIL import Image

# Configuration
CSV_FILE = 'profiles.csv'
PHOTOS_FOLDER = 'photos'

@st.cache_data # CRITICAL FIX: Cache the data load to prevent repeated file access and redirection loops
def load_data():
    """Loads the profile data from the CSV file, attempting to detect the correct delimiter."""
    try:
        # 1. First, attempt to detect the delimiter
        dialect = None
        # Use Streamlit's environment structure: paths are relative to the root of the app
        with open(CSV_FILE, 'r', newline='', encoding='utf-8') as f:
            # Read a small sample of the file to determine the dialect (including delimiter)
            sample = f.read(1024)
            # Check if sample is empty, indicating an empty file
            if not sample:
                st.error(f"Error: The file '{CSV_FILE}' is empty.")
                return pd.DataFrame()
            
            # Sniff the dialect only if there's content to sniff
            if sample.strip():
                dialect = csv.Sniffer().sniff(sample)
            else:
                # Default to comma if sample is all whitespace
                dialect = csv.excel()
                
        # 2. Read the CSV using the detected delimiter
        df = pd.read_csv(CSV_FILE, sep=dialect.delimiter, encoding='utf-8')
        
        # Ensure required columns are present and fix case
        required_cols_map = {
            'Name': 'Name', 
            'Birthday': 'Birthday', 
            'Town/County': 'Town/County', 
            'Country': 'Country' # Use the correct capitalization for keying
        }
        
        # Normalize column names in the DataFrame to handle inconsistent capitalization
        df.columns = [col.strip().replace('_', ' ') for col in df.columns]

        for required_col, target_col in required_cols_map.items():
            # Check for close matches (e.g., 'country', 'Country', 'COUNTRY')
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
                return pd.DataFrame() # Return empty DataFrame on failure

        # Final check to ensure all target columns exist after normalization
        if not all(col in df.columns for col in required_cols_map.values()):
             st.error("Column mapping failed after attempting to normalize names. Please verify your CSV headers.")
             return pd.DataFrame()

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
    the first name of the profile. This is highly flexible for existing filenames.
    """
    try:
        # Extract the first word (the first name) and normalize it
        # Example: "Ekene Amobi" -> "ekene"
        first_name = name.strip().split(' ')[0].lower()
        if not first_name:
            return None # Handle empty name string

        # Get the current working directory reliably
        current_dir = os.path.dirname(__file__) if '__file__' in locals() else os.getcwd()
        photos_dir = os.path.join(current_dir, PHOTOS_FOLDER)
        
        if not os.path.isdir(photos_dir):
            # Fallback for deployment environments where current_dir might be different
            photos_dir = PHOTOS_FOLDER
            if not os.path.isdir(photos_dir):
                return None 

        for filename in os.listdir(photos_dir):
            normalized_filename = filename.lower()
            
            # Check if the extracted first name is contained anywhere in the filename
            if first_name in normalized_filename:
                # Return the full path of the first match found
                return os.path.join(photos_dir, filename)
                
    except Exception as e:
        print(f"Error processing files in photos folder: {e}")
        
    return None

def display_profile_card(row):
    """Displays a single profile card, vertically stacked with a larger, centered photo."""
    
    image_path = get_image_path(row['Name'])

    # Create the main card container
    with st.container(border=True):
        
        # --- Image (Larger, Portrait Placeholder, and Centered) ---
        # Use three columns to push the image to the center of the card container
        col_left, col_img, col_right = st.columns([0.5, 3, 0.5])
        
        with col_img:
            image_width = 200 # Size for prominence
            
            if image_path and os.path.exists(image_path):
                try:
                    img = Image.open(image_path)
                    
                    # *** FIX FOR EXIF ORIENTATION ***
                    # This attempts to read and apply orientation fix from metadata
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
                except Exception as e:
                    # Fallback for image loading issues
                    st.warning(f"Could not load image for {row['Name']}.")
                    # Placeholder image to hint at portrait style (200x250)
                    st.image("https://placehold.co/200x250/CCCCCC/888888?text=No+Photo", width=image_width)
            else:
                # Placeholder image
                st.image("https://placehold.co/200x250/CCCCCC/888888?text=No+Photo", width=image_width)

        # --- Details (Beneath the photo, centered, reduced spacing) ---
        
        # Center the text using CSS in Markdown and reduce margin-top 
        # The <br> adds minimal spacing after the image
        st.markdown("<div style='text-align: center; margin-top: -15px;'>", unsafe_allow_html=True) 
        
        # Name (Larger font)
        st.markdown(f"**<span style='font-size: 1.4em;'>{row['Name']}</span>**", unsafe_allow_html=True)
        
        # Country
        st.markdown(f"*{row.get('Country', 'N/A')}*")
        
        # Birthday (with Cake emoji)
        st.markdown(f"<div style='font-size: 0.9em; color: #555; margin-top: 5px;'>🎂 {row.get('Birthday', 'N/A')}</div>", unsafe_allow_html=True)
        
        # Town/County (with House emoji)
        st.markdown(f"<div style='font-size: 0.9em; color: #555;'>🏠 {row.get('Town/County', 'N/A')}</div>", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)


def main():
    """Main function to run the Streamlit application."""
    st.set_page_config(layout="wide", page_title="Team Profiles")
    
    st.title("👥 Team Profiles")
    
    df = load_data()

    if df.empty:
        st.stop() # Stop if data loading failed

    # --- Filtering Sidebar ---
    st.sidebar.header("Find Profiles")

    # Name Search (case-insensitive partial match)
    search_query = st.sidebar.text_input("Search by Name", "")

    # Country Filter (Unique countries from data)
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

    st.markdown(f"---")
    st.header(f"Found {len(filtered_df)} Profiles")
    st.markdown("---")

    # --- Pinterest Grid Layout ---
    
    if filtered_df.empty:
        st.warning("No profiles match your search criteria.")
        return # Stop execution if no results

    # Define the number of columns for the grid (Pinterest style)
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
