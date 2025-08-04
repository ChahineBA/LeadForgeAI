from instagram import instagram
from website import AI_retriver
from data_cleaner import clean_data
import glob
import os

def process_file(input_file):
    base_name = os.path.basename(input_file)  # e.g., 'deel_1.csv'
    output_file = f"output_{base_name}"      # e.g., 'output_deel_1.csv'

    print(f"Starting data retrieval for {input_file}...")
    AI_retriver(input_file, output_file)
    
    print(f"Data retrieval completed for {input_file}. Now processing Instagram data...")
    instagram(output_file)

    print(f"Instagram data processing completed for {input_file}. Now cleaning data...")
    clean_data(output_file)

    print(f"Finished processing {input_file}.\n")

if __name__ == "__main__":
    input_files = glob.glob("files/deel_*.csv")  # Looks for files like files/deel_1.csv, files/deel_2.csv, etc.

    for input_file in input_files:
        process_file(input_file)
