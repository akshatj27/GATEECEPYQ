import requests
from bs4 import BeautifulSoup
import json
import os
import time
import logging
import re
from urllib.parse import urljoin, urlparse
import hashlib
from concurrent.futures import ThreadPoolExecutor

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("GATEScraper")

class GATEScraper:
    def __init__(self, base_url, output_dir="gate_questions", debug=False, max_threads=5):
        self.base_url = base_url
        self.output_dir = output_dir
        self.debug = debug
        self.max_threads = max_threads
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # Headers to mimic a browser
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        }
        
        # Track downloaded images to avoid duplicates
        self.downloaded_images = set()
    
    def get_soup(self, url):
        """Make a request to the URL and return BeautifulSoup object"""
        try:
            if self.debug:
                logger.info(f"Fetching: {url}")
            
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            if self.debug:
                logger.info(f"Status code: {response.status_code}")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            return soup
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            if self.debug:
                logger.exception(e)
            return None
    
    def get_year_links(self):
        """Extract links to all year pages"""
        try:
            soup = self.get_soup(self.base_url)
            if not soup:
                return []
            
            # Find all links in the page
            year_links = []
            links = soup.find_all('a')
            
            # Regular expression to match year and set links
            pattern = re.compile(r'gate-ec-\d{4}(?:-set-\d+)?$')
            
            for link in links:
                href = link.get('href')
                if href and pattern.search(href):
                    full_url = urljoin(self.base_url, href)
                    
                    # Extract year and set information
                    parts = href.split('-')
                    year = parts[-1] if '-set-' not in href else parts[-3]
                    
                    # If it's a set, include that info
                    if '-set-' in href:
                        set_num = parts[-1]
                        year_set_key = f"{year}-set-{set_num}"
                        year_links.append((year, year_set_key, full_url))
                    else:
                        year_links.append((year, year, full_url))
            
            if self.debug:
                logger.info(f"Found {len(year_links)} year/set links: {year_links}")
            
            # If no links found, fall back to a predefined range
            if not year_links:
                logger.warning("No year links found, using predefined range")
                years = list(range(2010, 2025))
                year_links = [(str(year), str(year), f"https://practicepaper.in/gate-ec/gate-ec-{year}") for year in years]
            
            return year_links
        except Exception as e:
            logger.error(f"Error getting year links: {e}")
            if self.debug:
                logger.exception(e)
            return []
    
    def get_page_count(self, year_url):
        """Get the number of pages for a specific year"""
        try:
            soup = self.get_soup(year_url)
            if not soup:
                return 1
            
            # Find pagination links
            pagination = soup.select("ul.pagination li a")
            
            max_page = 1
            for page_link in pagination:
                text = page_link.text.strip()
                if text.isdigit():
                    page_num = int(text)
                    max_page = max(max_page, page_num)
            
            if self.debug:
                logger.info(f"Found {max_page} pages for {year_url}")
                
            return max_page
        except Exception as e:
            logger.error(f"Error getting page count for {year_url}: {e}")
            if self.debug:
                logger.exception(e)
            return 1
    
    def download_image(self, image_url, year_dir, image_folder="images"):
        """Download an image and save it locally"""
        try:
            # Skip if already downloaded
            if image_url in self.downloaded_images:
                # Return the previously saved path
                file_hash = hashlib.md5(image_url.encode('utf-8')).hexdigest()
                image_filename = f"{file_hash}.jpg"
                return os.path.join(image_folder, image_filename)
            
            # Create image directory if it doesn't exist
            images_dir = os.path.join(year_dir, image_folder)
            os.makedirs(images_dir, exist_ok=True)
            
            # Get the full image URL
            full_image_url = urljoin(self.base_url, image_url)
            
            # Create a filename based on the URL hash to avoid duplicates
            file_hash = hashlib.md5(image_url.encode('utf-8')).hexdigest()
            
            # Extract the file extension from the URL or default to .jpg
            parsed_url = urlparse(image_url)
            path = parsed_url.path
            ext = os.path.splitext(path)[1]
            if not ext or ext.lower() not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                ext = '.jpg'
            
            image_filename = f"{file_hash}{ext}"
            image_path = os.path.join(images_dir, image_filename)
            
            # Check if the image already exists
            if os.path.exists(image_path):
                if self.debug:
                    logger.info(f"Image already exists: {image_path}")
                self.downloaded_images.add(image_url)
                return os.path.join(image_folder, image_filename)
            
            # Download and save the image
            response = requests.get(full_image_url, headers=self.headers, stream=True)
            response.raise_for_status()
            
            with open(image_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            if self.debug:
                logger.info(f"Downloaded image: {image_url} to {image_path}")
            
            # Add to downloaded set
            self.downloaded_images.add(image_url)
            
            return os.path.join(image_folder, image_filename)
        except Exception as e:
            logger.error(f"Error downloading image {image_url}: {e}")
            if self.debug:
                logger.exception(e)
            return None
    
    def extract_and_replace_images(self, html_element, year_dir):
        """
        Extract images from HTML content, download them, and replace src with local paths.
        Returns modified HTML content with updated image paths and a dict of image sources to local paths.
        """
        if not html_element:
            return html_element, {}
        
        image_map = {}  # Map of original image URLs to local paths
        
        # Find all images in the HTML
        for img in html_element.find_all('img'):
            src = img.get('src')
            data_src = img.get('data-src')
            
            # Get the actual image URL (prefer data-src as it often contains the real path)
            img_url = data_src if data_src else src
            
            # Skip base64 and placeholder images
            if not img_url or img_url.startswith('data:'):
                continue
            
            # Download the image
            local_path = self.download_image(img_url, year_dir)
            if local_path:
                # Update the image attributes
                img['src'] = f'gate_questions/{os.path.basename(year_dir)}/{local_path}'
                if 'data-src' in img.attrs:
                    del img['data-src']  # Remove data-src to prevent lazyloading issues
                
                # Store mapping of original URL to local path
                image_map[img_url] = local_path
        
        return html_element, image_map
    
    def extract_question_content(self, question_div, year_dir):
        """Extract the content of a question including images and maintain their positions"""
        try:
            # Extract question number
            question_label = question_div.select_one(".question_lable")
            question_number = question_label.text.strip() if question_label else "Unknown"
            
            # Extract question text with images in place
            question_text_div = question_div.select_one(".question_text")
            
            # Process question text and images
            question_html = ""
            question_images = {}
            
            if question_text_div:
                # Process images in the question text
                processed_div, images = self.extract_and_replace_images(question_text_div, year_dir)
                question_html = str(processed_div)
                question_images.update(images)
                
                # Get plain text for searchability
                question_text = processed_div.get_text(separator=" ", strip=True)
            else:
                question_text = ""
            
            # Determine question type (MCQ or numerical)
            option_rows = question_div.select(".answer_table tbody tr")
            is_numerical = len(option_rows) == 0
            
            # Extract common fields first
            question_data = {
                "number": question_number,
                "text": question_text,
                "html": question_html,
                "images": question_images,
                "type": "numerical" if is_numerical else "mcq",
            }
            
            # Extract subject/topic if available
            subject_div = question_div.select_one(".year_sub_chap_link")
            if subject_div:
                subject_links = subject_div.find_all('a')
                subject = ' - '.join([link.get_text(strip=True) for link in subject_links]) if subject_links else ""
                question_data["subject"] = subject
            
            # Extract explanation if available
            explanation_div = question_div.select_one(".mtq_explanation-text")
            if explanation_div:
                # Process images in explanation
                processed_div, images = self.extract_and_replace_images(explanation_div, year_dir)
                explanation_html = str(processed_div)
                explanation_text = processed_div.get_text(separator=" ", strip=True)
                question_data["explanation_text"] = explanation_text
                question_data["explanation_html"] = explanation_html
                question_data["explanation_images"] = images
            
            # Type-specific fields
            if is_numerical:
                # For numerical questions, extract answer range from button
                answer_min = None
                answer_max = None
                
                check_answer_btn = question_div.select_one(".checkansbtn")
                if check_answer_btn:
                    # Extract the acceptable range from data attributes
                    min_val = check_answer_btn.get('data-value1')
                    max_val = check_answer_btn.get('data-value2')
                    
                    if min_val:
                        try:
                            answer_min = float(min_val)
                        except:
                            pass
                    
                    if max_val:
                        try:
                            answer_max = float(max_val)
                        except:
                            pass
                
                # Try to extract answers from explanation if not found through button
                if not answer_min and "explanation_text" in question_data:
                    # Common patterns for answers in explanations
                    answer_patterns = [
                        r'answer is (\d+\.?\d*)',
                        r'answer: (\d+\.?\d*)',
                        r'= (\d+\.?\d*)$'
                    ]
                    
                    for pattern in answer_patterns:
                        match = re.search(pattern, question_data["explanation_text"], re.IGNORECASE)
                        if match:
                            try:
                                answer_min = float(match.group(1))
                                answer_max = answer_min  # Set same value for both if single answer
                                break
                            except ValueError:
                                pass
                
                # Only add answer fields if we found values
                if answer_min is not None:
                    question_data["answer_min"] = answer_min
                if answer_max is not None:
                    question_data["answer_max"] = answer_max
                    
            else:
                # For MCQ questions, extract options and correct answers
                options = []
                for row in option_rows:
                    option_letter_div = row.select_one(".option_index_number")
                    option_text_div = row.select_one(".option_data")
                    
                    if option_letter_div and option_text_div:
                        option_letter = option_letter_div.get_text(strip=True)
                        
                        # Process images in option
                        processed_div, option_images = self.extract_and_replace_images(option_text_div, year_dir)
                        option_html = str(processed_div)
                        option_text = processed_div.get_text(separator=" ", strip=True)
                        
                        # Check if this option is marked as correct
                        marker_div = row.select_one(".mtq_correct_marker")
                        is_correct = marker_div is not None
                        
                        options.append({
                            "letter": option_letter,
                            "text": option_text,
                            "html": option_html,
                            "is_correct": is_correct,
                            "images": option_images
                        })
                
                question_data["options"] = options
                
                # Add a direct "answer" field with the correct option letter(s)
                correct_options = [opt["letter"] for opt in options if opt["is_correct"]]
                if correct_options:
                    question_data["answer"] = correct_options[0] if len(correct_options) == 1 else correct_options
            
            return question_data
        except Exception as e:
            logger.error(f"Error extracting question content: {e}")
            if self.debug:
                logger.exception(e)
            return None
    
    def extract_questions(self, page_url, year_dir):
        """Extract all questions from a page"""
        try:
            soup = self.get_soup(page_url)
            if not soup:
                return []
            
            # Find all question divs
            question_divs = soup.select("div.question")
            
            if self.debug:
                logger.info(f"Found {len(question_divs)} questions on {page_url}")
            
            questions = []
            for div in question_divs:
                question_data = self.extract_question_content(div, year_dir)
                if question_data:
                    question_data["source_url"] = page_url
                    questions.append(question_data)
            
            return questions
        except Exception as e:
            logger.error(f"Error extracting questions from {page_url}: {e}")
            if self.debug:
                logger.exception(e)
            return []
    
    def download_year_questions(self, year, year_set_key, year_url):
        """Download questions for a specific year/set"""
        try:
            # Create year directory (include set info in directory name if present)
            year_dir = os.path.join(self.output_dir, f"gate_ec_{year_set_key}")
            os.makedirs(year_dir, exist_ok=True)
            
            # Get the number of pages for this year
            page_count = self.get_page_count(year_url)
            
            # Process each page
            year_questions = []
            for page_num in range(1, page_count + 1):
                page_url = f"{year_url}?page_no={page_num}" if page_num > 1 else year_url
                
                if self.debug:
                    logger.info(f"Processing year {year_set_key}, page {page_num}/{page_count}: {page_url}")
                
                # Extract questions from this page
                questions = self.extract_questions(page_url, year_dir)
                year_questions.extend(questions)
                
                # Sleep to avoid overwhelming the server
                time.sleep(1)
            
            # Save year data to file
            year_file = os.path.join(year_dir, f"questions.json")
            with open(year_file, 'w', encoding='utf-8') as f:
                json.dump(year_questions, f, ensure_ascii=False, indent=2)
            
            if self.debug:
                logger.info(f"Saved {len(year_questions)} questions for year {year_set_key}")
            
            return year_questions
        except Exception as e:
            logger.error(f"Error processing year {year_set_key}: {e}")
            if self.debug:
                logger.exception(e)
            return []
    
    def run(self):
        """Main method to run the scraper"""
        try:
            # Get all year links
            year_links = self.get_year_links()
            
            if not year_links:
                logger.error("No year links found. Exiting.")
                return False
            
            all_data = {}
            
            # Sort year links by year (descending)
            year_links.sort(key=lambda x: x[0], reverse=True)
            
            # Create thread pool for parallel downloads
            with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
                # Submit all year processing tasks
                future_to_year = {
                    executor.submit(self.download_year_questions, year, year_set_key, year_url): (year, year_set_key, year_url) 
                    for year, year_set_key, year_url in year_links
                }
                
                # Process results as they complete
                for future in future_to_year:
                    year, year_set_key, _ = future_to_year[future]
                    try:
                        year_questions = future.result()
                        all_data[year_set_key] = year_questions
                    except Exception as e:
                        logger.error(f"Error processing year {year_set_key}: {e}")
            
            # Save all data to a combined file
            all_data_file = os.path.join(self.output_dir, "gate_ec_all_years.json")
            with open(all_data_file, 'w', encoding='utf-8') as f:
                json.dump(all_data, f, ensure_ascii=False, indent=2)
            
            if self.debug:
                logger.info(f"All data saved successfully")
            
            return True
        except Exception as e:
            logger.error(f"Error in scraper run: {e}")
            if self.debug:
                logger.exception(e)
            return False

    def debug_page(self, url):
        """Debug a specific page"""
        logger.info(f"Debugging page: {url}")
        
        soup = self.get_soup(url)
        if not soup:
            logger.error("Failed to fetch the page")
            return
        
        # Check for pagination
        pagination = soup.select("ul.pagination li a")
        logger.info(f"Pagination elements: {len(pagination)}")
        
        # Check for questions
        question_divs = soup.select("div.question")
        logger.info(f"Question elements: {len(question_divs)}")
        
        if len(question_divs) == 0:
            logger.error("No questions found! Dumping page structure...")
            
            # Save the HTML for inspection
            debug_file = os.path.join(self.output_dir, "debug_page.html")
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(str(soup))
            logger.info(f"Saved page HTML to {debug_file}")
            
            # Look for potential class name differences
            potential_question_divs = soup.find_all("div", class_=lambda c: c and "question" in c)
            logger.info(f"Found {len(potential_question_divs)} potential question divs")
        else:
            logger.info("Found questions, examining structure...")
            
            # Examine first question
            div = question_divs[0]
            
            # Question text
            question_text_div = div.select_one(".question_text")
            if question_text_div:
                logger.info(f"Question text: {question_text_div.get_text(strip=True)[:100]}...")
                
                # Check for LaTeX content
                latex_content = re.findall(r'\[latex\](.*?)\[/latex\]', str(question_text_div))
                logger.info(f"LaTeX expressions: {len(latex_content)}")
                
                # Check for images
                images = question_text_div.find_all('img')
                logger.info(f"Question has {len(images)} images")
                
                for i, img in enumerate(images):
                    logger.info(f"Image {i+1} src: {img.get('src')}")
                    logger.info(f"Image {i+1} data-src: {img.get('data-src')}")
            
            # Check if multiple choice or numerical
            option_table = div.select_one(".answer_table")
            if option_table:
                option_rows = option_table.select("tbody tr")
                logger.info(f"Question has {len(option_rows)} options")
                
                # Check for correct answer marker
                correct_markers = div.select(".mtq_correct_marker")
                logger.info(f"Found {len(correct_markers)} correct answer markers")
            else:
                logger.info("This appears to be a numerical question (no options)")
            
            # Explanation
            explanation_div = div.select_one(".mtq_explanation-text")
            if explanation_div:
                logger.info(f"Has explanation: {explanation_div.get_text(strip=True)[:100]}...")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Scrape GATE EC questions with images")
    parser.add_argument("--output", default="gate_questions", help="Output directory for questions")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--debug-page", help="Debug a specific page URL")
    parser.add_argument("--year", help="Scrape a specific year only (e.g., 2024)")
    parser.add_argument("--set", help="Scrape a specific set number (e.g., 1)")
    parser.add_argument("--threads", type=int, default=5, help="Maximum number of threads to use")
    
    args = parser.parse_args()
    
    base_url = "https://practicepaper.in/gate-ec/gate-ec-year-wise-questions"
    scraper = GATEScraper(base_url, output_dir=args.output, debug=args.debug, max_threads=args.threads)
    
    if args.debug_page:
        # Debug a specific page
        scraper.debug_page(args.debug_page)
    elif args.year:
        # Scrape a specific year
        if args.set:
            year_url = f"https://practicepaper.in/gate-ec/gate-ec-{args.year}-set-{args.set}"
            year_set_key = f"{args.year}-set-{args.set}"
        else:
            year_url = f"https://practicepaper.in/gate-ec/gate-ec-{args.year}"
            year_set_key = args.year
            
        logger.info(f"Scraping specific year: {year_set_key} from {year_url}")
        
        # Create year directory
        year_dir = os.path.join(args.output, f"gate_ec_{year_set_key}")
        os.makedirs(year_dir, exist_ok=True)
        
        year_questions = scraper.download_year_questions(args.year, year_set_key, year_url)
        
        logger.info(f"Saved {len(year_questions)} questions for year {year_set_key}")
    else:
        # Run the full scraper
        success = scraper.run()
        
        if success:
            print(f"Successfully scraped questions with images to {args.output}")
        else:
            print("Failed to scrape questions. Check scraper.log for details.")
