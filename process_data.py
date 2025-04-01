import os
import json
import re
import logging
from pathlib import Path

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
    Compile all individual year JSON files into a single JSON file with years as keys
    """
    logger.info(f"Starting compilation of JSON files from {input_dir}")
    
    # Dictionary to hold all questions by year
    all_data = {}
    
    # Find all gate_ec_* directories
    base_path = Path(input_dir)
    year_dirs = [d for d in base_path.iterdir() if d.is_dir() and d.name.startswith("gate_ec_")]
    
    if not year_dirs:
        logger.error(f"No gate_ec_* directories found in {input_dir}")
        return False
    
    logger.info(f"Found {len(year_dirs)} year directories")
    
    # Process each year directory
    for year_dir in year_dirs:
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
    
    # Save combined data
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Successfully compiled {len(all_data)} years/sets of questions into {output_file}")
        return True
    except Exception as e:
        logger.error(f"Error saving compiled data to {output_file}: {e}")
        return False

if __name__ == "__main__":
    compile_json_files()
    logger.info("Process completed")