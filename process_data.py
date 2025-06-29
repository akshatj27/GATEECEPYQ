import os
import json
import re
import logging
from pathlib import Path
from collections import OrderedDict
import argparse

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("process_data.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("DataProcessor")

def compile_json_files(branch='ec', input_dir="gate_questions"):
    """
    Compile all individual year JSON files for a specific branch into a single JSON file.
    Special directories for aptitude and engineering mathematics are also included.
    """
    branch = branch.lower()
    output_file = f"gate_{branch}_all_years.json"
    
    logger.info(f"Starting compilation for branch '{branch.upper()}' from '{input_dir}' into '{output_file}'")
    
    # Dictionary to hold all questions by year
    all_data = {}
    # List to track special directories that should appear at the end
    special_dirs = []
    
    # Find all relevant directories for the branch and the special subjects
    base_path = Path(input_dir)
    if not base_path.exists():
        logger.error(f"Input directory '{input_dir}' not found. Please run the scraper first.")
        return False
        
    # Find directories matching the branch pattern OR the dummy/special patterns
    year_dirs = [d for d in base_path.iterdir() if d.is_dir() and (
        d.name.startswith(f"gate_{branch}_") or 
        d.name.startswith("gate_dummy_aptitude") or
        d.name.startswith("gate_dummy_engineering_mathematics")
    )]
    
    if not year_dirs:
        logger.error(f"No 'gate_{branch}_*' or special directories found in '{input_dir}'")
        return False
    
    logger.info(f"Found {len(year_dirs)} year/special directories to process.")
    
    # Process each year directory
    for year_dir in year_dirs:
        # Special handling for the dummy directories
        if "dummy_aptitude" in year_dir.name:
            year_key = "dummy_aptitude"
            special_dirs.append(year_key)
            logger.info(f"Processing special directory: {year_dir.name} as {year_key}")
        elif "dummy_engineering_mathematics" in year_dir.name:
            year_key = "dummy_engineering_mathematics"
            special_dirs.append(year_key)
            logger.info(f"Processing special directory: {year_dir.name} as {year_key}")
        else:
            # Extract year and set info from branch-specific directory name
            year_match = re.search(rf'gate_{branch}_(\d{{4}})(?:-set-(\d+))?', year_dir.name)
            if not year_match:
                logger.warning(f"Could not extract year from directory: {year_dir.name}, skipping")
                continue
                
            year_number = year_match.group(1)  # Extract the year number (e.g., "2024")
            set_number = year_match.group(2)   # Extract the set number if it exists
            
            # Create the appropriate key for the JSON output
            if set_number:
                year_key = f"{year_number}-set-{set_number}"
            else:
                year_key = year_number
        
        # Check if questions.json exists
        questions_file = year_dir / "questions.json"
        if not questions_file.exists():
            logger.warning(f"No questions.json found in {year_dir}, skipping")
            continue
        
        # Read questions
        try:
            with open(questions_file, 'r', encoding='utf-8') as f:
                questions = json.load(f)
            
            # If it's a list, use it directly
            if isinstance(questions, list):
                all_data[year_key] = questions
                logger.info(f"Added {len(questions)} questions for key '{year_key}'")
            else:
                logger.warning(f"Questions data in {questions_file} is not a list, skipping")
                continue
                
        except Exception as e:
            logger.error(f"Error processing {questions_file}: {e}")
            continue
    
    # Reorder the data so special directories appear at the end
    ordered_data = OrderedDict()
    
    # First add all regular year entries (sorted by year)
    regular_years = [(k, v) for k, v in all_data.items() if k not in special_dirs]
    regular_years.sort(key=lambda x: x[0], reverse=True)  # Sort by year-set string in descending order
    
    for year_key, questions in regular_years:
        ordered_data[year_key] = questions
    
    # Then add special directory entries
    for special_key in sorted(list(set(special_dirs))): # Sort to ensure consistent order
        if special_key in all_data:
            ordered_data[special_key] = all_data[special_key]
    
    # Save combined data
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(ordered_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Successfully compiled {len(ordered_data)} years/sets of questions into {output_file}")
        return True
    except Exception as e:
        logger.error(f"Error saving compiled data to {output_file}: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compile scraped GATE questions into a single JSON file for a specific branch.")
    parser.add_argument("--branch", default="ec", help="Specify the GATE branch to process (e.g., ec, ee, me, cse)")
    parser.add_argument("--input", default="gate_questions", help="Input directory where scraped data is stored")
    
    args = parser.parse_args()
    
    compile_json_files(branch=args.branch, input_dir=args.input)
    logger.info("Process completed")