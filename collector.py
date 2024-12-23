import json
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from MCQA_generator import MedFactsExtractor, MCQModule
from MCQA_processor import MCQDataProcessor
from ingest import Ingest
from models import Base
from tabulate import tabulate
import datetime
import argparse
import sys
import os

# Add the src/utils directory to the Python path
utils_path = os.path.join(os.path.dirname(__file__), 'src', 'utils')
sys.path.append(utils_path)

# Add the src directory to the Python path
src_path = os.path.join(os.path.dirname(__file__), 'src')
sys.path.append(src_path)

from multimodal.litellm_image_processing import MediaBatchProcessor
from helper.web_gateway.image_capture import ImageCaptureGateway

# Disable LiteLLM specific logging to prevent AttributeError
logging.getLogger('LiteLLM').setLevel(logging.CRITICAL)

class Collector:
    def __init__(self, database_url, model_name="gpt-4o", media_model="ollama/llava"):
        """
        Initialize the Collector class.

        Parameters:
        - database_url (str): The database connection URL.
        - model_name (str): The name of the language model to use for text processing.
        - media_model (str): The name of the model to use for media processing.
        """
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(self.__class__.__name__)

        # Setup database
        self.engine = create_engine(database_url)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Initialize components
        self.extractor = MedFactsExtractor(model_name)
        self.mcq_module = MCQModule()
        self.media_processor = MediaBatchProcessor(model=media_model)

    def process_and_ingest(self, text_corpus):
        """
        Process the text corpus to generate MCQs and ingest them into the database.

        Parameters:
        - text_corpus (str): The input text to be processed.
        """
        # Generate facts from the text corpus
        json_output = self.extractor.process_text_to_facts(text_corpus)
        facts_list = json.loads(json_output)

        # Generate MCQs from facts
        all_questions = []
        for fact in facts_list:
            input_text = f"Subject: {fact['subject']}. Fact: {fact['fact']}"
            response = self.mcq_module.forward(input_text)
            if 'questions' in response:
                all_questions.extend(response['questions'])

        print(all_questions)

        # Process MCQs
        processor = MCQDataProcessor({'questions': all_questions})
        processed_data = processor.extract_relevant_data()

        # Ingest MCQs into the database
        session = self.SessionLocal()
        try:
            ingest = Ingest(session)
            all_questions_json = []  # List to hold all question JSONs
            for question in processed_data:
                all_questions_json.append(question)
                ingest.ingest_single(question)

            # Create table data from the questions
            table_data = [[
                q.get('question_text', ''),
                # Parse JSON string of options if needed, otherwise join the list directly
                ', '.join(json.loads(q.get('options')) if isinstance(q.get('options'), str) else q.get('options', [])),
                q.get('correct_option', ''),
                q.get('subject', ''),
                q.get('sub_subject', ''),
                q.get('difficulty', ''),
                q.get('reasoning', ''),
                datetime.datetime.utcnow(),
                datetime.datetime.utcnow()
            ] for q in all_questions_json]

            # Define headers for the table
            headers = [
                'Question Text', 
                'Options', 
                'Correct Option', 
                'Subject',
                'Sub Subject',
                'Difficulty',
                'Reasoning',
                'Created At',
                'Updated At'
            ]
            
            # Display the table
            print("\nGenerated Questions:")
            print(tabulate(table_data, headers=headers, tablefmt='grid'))

            session.commit()
            self.logger.info("All questions ingested successfully.")
        except Exception as e:
            session.rollback()
            self.logger.error(f"An error occurred during ingestion: {e}")
        finally:
            session.close()

    def process_text(self, text):
        """
        Process the text to generate MCQs and ingest them into the database.

        Parameters:
        - text (str): The input text to be processed.
        """
        self.process_and_ingest(text)

def main():
    parser = argparse.ArgumentParser(description="Run the Collector")
    parser.add_argument('--web', action='store_true', help="Run the web server for multimodal input")
    args = parser.parse_args()

    DATABASE_URL = "postgresql+psycopg2://postgresUser:postgresPW@localhost:5455/postgresDB"
    TEXT_MODEL_NAME = "gpt-4o"  # Model for text processing
    MEDIA_MODEL_NAME = "openai/gpt-4o-mini"  # Model for media processing

    collector = Collector(DATABASE_URL, model_name=TEXT_MODEL_NAME, media_model=MEDIA_MODEL_NAME)

    if args.web:
        # from CureIQ.src.helper.web_gateway.image_capture import ImageCaptureGateway
        app_instance = ImageCaptureGateway(collector)
        app_instance.run()
    else:
        text_corpus = input("Enter the text to convert into facts:")
        collector.process_and_ingest(text_corpus)

if __name__ == "__main__":
    main() 