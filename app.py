import streamlit as st
import pandas as pd
import os
import csv 
from PIL import Image

# Configuration
CSV_FILE = 'profiles.csv'
PHOTOS_FOLDER = 'photos'

def load_data():
    """Loads the profile data from the CSV file, attempting to detect the correct delimiter."""
    try:
        # 1. First, attempt to detect the delimiter
        dialect = None
        with open(CSV_FILE, 'r', newline='', encoding='utf-8') as f:
            # Read a small sample of the file to determine the dialect (including delimiter)
            sample = f.read(1024)
            dialect = csv.Sniffer().sniff(sample)

        # 2. Read the CSV using the detected delimiter
        df = pd.read_csv(CSV_FILE, sep=dialect.delimiter, encoding='utf-8')
        
        # Ensure required columns are present.
        required_cols = ['Name', 'Birthday', 'Town/County', 'Country']
        for col in required_cols:
            if col not in df.columns:
                st.error(f"Error: The required column '{col}' is missing from '{CSV_FILE}'.")
                st.info("Please ensure your CSV file has the exact column headers: 'Name', 'Birthday', 'Town/County', 'Country'")
                return pd.DataFrame() # Return empty DataFrame on failure

        # Convert Name to string and fill NaNs
        df['Name'] = df['Name'].astype(str).fillna('Unknown Profile')
        return df
    except FileNotFoundError:
        st.error(f"Error: The file '{CSV_FILE}' was not found. Please place it in the application directory.")
        return pd.DataFrame()
    except Exception as e:
        # Catch the tokenization error and provide a more helpful message
        st.error(f"An unexpected error occurred while loading the CSV: {e}")
        st.warning("If this is a tokenizing error, your file might not be a standard CSV. Please open it, ensure it only contains text data, and save it explicitly as 'CSV (Comma delimited)'.")
        return pd.DataFrame()

def get_image_path(name):
    """
    Finds the image file in the photos folder where the filename contains
    the first name of the profile. This is highly flexible for existing filenames.
    """
    try:
        # CRITICAL CHANGE: Extract the first word (the first name) and normalize it
        # Example: "Ekene Amobi" -> "ekene"
        first_name = name.strip().split(' ')[0].lower()
        if not first_name:
            return None # Handle empty name string

        # List all files in the photos directory
        for filename in os.listdir(PHOTOS_FOLDER):
            # Normalize the filename for case-insensitive checking
            normalized_filename = filename.lower()
            
            # Check if the extracted first name is contained anywhere in the filename
            # This handles files like 'Ekene.jpg', 'Ekene Amobi.jpg', '2023-06-01~2 - Ekene amobi.jpg', etc.
            if first_name in normalized_filename:
                # Return the full path of the first match found
                return os.path.join(PHOTOS_FOLDER, filename)
                
    except FileNotFoundError:
        # If the photos folder doesn't exist, this function will fail gracefully.
        pass
    except Exception as e:
        # Print error for debugging, but continue
        print(f"Error processing files in photos folder: {e}")
        
    # If no image found after checking all files, return None
    return None

def display_profile_card(row):
    """Displays a single profile card, now vertically stacked with a larger, centered photo,
    and attempts to fix image orientation based on EXIF data."""
    
    image_path = get_image_path(row['Name'])

    # Create the main card container
    with st.container(border=True):
        
        # --- Image (Larger, Portrait Placeholder, and Centered) ---
        # Use three columns to push the image to the center of the card container
        col_left, col_img, col_right = st.columns([0.5, 3, 0.5])
        
        with col_img:
            image_width = 200 # Slightly increased size for prominence
            
            if image_path:
                try:
                    img = Image.open(image_path)
                    
                    # *** FIX FOR EXIF ORIENTATION ***
                    # Checks for orientation tag and fixes rotation in place
                    if hasattr(img, '_getexif') and img._getexif():
                        exif = dict(img._getexif().items())
                        orientation = exif.get(0x0112) # 0x0112 is the EXIF Orientation tag
                        
                        if orientation == 3:
                            img = img.transpose(Image.ROTATE_180)
                        elif orientation == 6:
                            img = img.transpose(Image.ROTATE_270)
                        elif orientation == 8:
                            img = img.transpose(Image.ROTATE_90)
                    
                    # Streamlit will maintain the aspect ratio, but we set a larger width
                    st.image(img, width=image_width) 
                except Exception as e:
                    # Fallback for image loading issues
                    st.warning(f"Could not load image for {row['Name']}. Error: {e}")
                    # Placeholder image to hint at portrait style (200x250)
                    st.image("https://placehold.co/200x250/CCCCCC/888888?text=No+Photo", width=image_width)
            else:
                # Placeholder image
                st.image("https://placehold.co/200x250/CCCCCC/888888?text=No+Photo", width=image_width)

        # --- Details (Beneath the photo, centered) ---
        # The text now stacks vertically below the image columns.
        
        # Center the text using CSS in Markdown and reduce margin-top to 0px 
        # for minimal spacing between the photo and the details.
        st.markdown("<div style='text-align: center; margin-top: 0px;'>", unsafe_allow_html=True)
        
        # Name (Larger font)
        st.markdown(f"**<span style='font-size: 1.4em;'>{row['Name']}</span>**", unsafe_allow_html=True)
        
        # Country
        st.markdown(f"*{row.get('Country', 'N/A')}*")
        
        # Birthday (with Cake emoji)
        st.markdown(f"<div style='font-size: 0.9em; color: #555;'>🎂 {row.get('Birthday', 'N/A')}</div>", unsafe_allow_html=True)
        
        # Town/County (with House emoji)
        st.markdown(f"<div style='font-size: 0.9em; color: #555;'>🏠 {row.get('Town/County', 'N/A')}</div>", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)


def main():
    """Main function to run the Streamlit application."""
    st.set_page_config(layout="wide", page_title="Group Profiles")
    
    st.title("👥 Group Profiles")
    
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
        # Place the card in the current column (col_index)
        with cols[col_index]:
            display_profile_card(row)
            # Add a small separator inside the column for vertical stacking
            st.markdown("<br>", unsafe_allow_html=True) 
            
        # Move to the next column, wrapping around (0 -> 1 -> 2 -> 0 -> ...)
        col_index = (col_index + 1) % NUM_COLUMNS
        
    st.markdown("<br><br>", unsafe_allow_html=True) 


if __name__ == '__main__':
    main()
