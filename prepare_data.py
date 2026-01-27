import pandas as pd
from datetime import timedelta

def prepare_data():
    input_file = "311_Service_Requests_October_1,_2020_to_Present_20260127.csv"
    output_file = "311_Lite.csv"
    
    print("Loading data...")
    # Read only necessary columns if possible, but we need to know them. Reading all for now.
    # low_memory=False avoids mixed type warnings on large files
    try:
        df = pd.read_csv(input_file, low_memory=False)
    except FileNotFoundError:
        print(f"Error: {input_file} not found.")
        return

    print("Converting 'Created Date' to datetime...")
    # Coerce errors to NaT to avoid crashing on bad dates
    df['Created Date'] = pd.to_datetime(df['Created Date'], errors='coerce')
    
    # Calculate cutoff date
    # Using the current system time as 'today'
    end_date = pd.Timestamp.now()
    start_date = end_date - pd.DateOffset(months=6)
    
    print(f"Filtering data from {start_date} to {end_date}...")
    
    df_lite = df[df['Created Date'] > start_date].copy()
    
    print(f"Original rows: {len(df)}")
    print(f"Filtered rows: {len(df_lite)}")
    
    print(f"Saving to {output_file}...")
    df_lite.to_csv(output_file, index=False)
    print("Done.")

if __name__ == "__main__":
    prepare_data()
