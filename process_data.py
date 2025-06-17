import os
import json
import re
import logging
from pathlib import Path
from collections import OrderedDict

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

def compile_json_files(input_dir="gate_questions", output_file="gate_ec_all_years.json"):
    """
    Compile all individual year JSON files into a single JSON file with years as keys.
    Special directories for aptitude and engineering mathematics are included
    but placed at the end of the JSON structure.
    """
    logger.info(f"Starting compilation of JSON files from {input_dir}")
      # Dictionary to hold all questions by year
    all_data = {}
    # List to track special directories that should appear at the end
    special_dirs = []
    
    # Find all gate_ec_* directories and special directories
    base_path = Path(input_dir)
    # Updated to include both special directories
    year_dirs = [d for d in base_path.iterdir() if d.is_dir() and (
        d.name.startswith("gate_ec_") or 
        d.name == "gate_dummy_aptitude_other_branches" or
        d.name == "gate_dummy_engineering_mathematics_other_branches"
    )]
    
    if not year_dirs:
        logger.error(f"No gate_ec_* or special directories found in {input_dir}")
        return False
    
    logger.info(f"Found {len(year_dirs)} year/special directories")
    
    # Process each year directory
    for year_dir in year_dirs:        # Special handling for the dummy directories
        if year_dir.name == "gate_dummy_aptitude_other_branches":
            year_key = "dummy_aptitude"
            special_dirs.append(year_key)
            logger.info(f"Processing special directory: {year_dir.name} as {year_key}")
        elif year_dir.name == "gate_dummy_engineering_mathematics_other_branches":
            year_key = "dummy_engineering_mathematics"
            special_dirs.append(year_key)
            logger.info(f"Processing special directory: {year_dir.name} as {year_key}")
        else:
            # Extract year and set info from directory name (gate_ec_YYYY or gate_ec_YYYY-set-N)
            year_match = re.search(r'gate_ec_(\d{4})(?:-set-(\d+))?', year_dir.name)
            if not year_match:
                logger.warning(f"Could not extract year from directory: {year_dir.name}, skipping")
                continue
                
            year_number = year_match.group(1)  # Extract the year number (e.g., "2001")
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
            
            # If it's already a list, use it directly
            if isinstance(questions, list):
                all_data[year_key] = questions
                logger.info(f"Added {len(questions)} questions for {year_key}")
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
    regular_years.sort(key=lambda x: x[0], reverse=True)  # Sort by year in descending order
    
    for year_key, questions in regular_years:
        ordered_data[year_key] = questions
    
    # Then add special directory entries
    for special_key in special_dirs:
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
    compile_json_files()
    logger.info("Process completed")