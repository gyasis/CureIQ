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

# Disable LiteLLM specific logging to prevent AttributeError
logging.getLogger('LiteLLM').setLevel(logging.CRITICAL)

class Collector:
    def __init__(self, database_url, model_name="gpt-4o"):
        """
        Initialize the Collector class.

        Parameters:
        - database_url (str): The database connection URL.
        - model_name (str): The name of the language model to use.
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

def main():
    DATABASE_URL = "postgresql+psycopg2://postgresUser:postgresPW@localhost:5455/postgresDB"
    collector = Collector(DATABASE_URL)
    text_corpus = input("Enter the text to convert into facts:")
    collector.process_and_ingest(text_corpus)

if __name__ == "__main__":
    main() 