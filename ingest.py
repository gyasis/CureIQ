# ingest.py
import json
import datetime
import logging
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from models import Question
import sqlalchemy

class Ingest:
    def __init__(self, session: Session, batch_size: int = 100):
        """
        Initialize the Ingest class with a SQLAlchemy session and batch size.

        Parameters:
        - session (Session): SQLAlchemy session object connected to the database.
        - batch_size (int): Number of records to insert per batch during bulk ingestion.
        """
        self.session = session
        self.batch_size = batch_size
        self.logger = logging.getLogger(self.__class__.__name__)

    def ingest_single(self, question_data):
        """
        Ingest a single MCQ into the PostgreSQL database.

        Parameters:
        - question_data (dict): Dictionary containing the MCQ data.

        Returns:
        - None
        """
        try:
            # Check for mandatory fields
            if not all([
                question_data.get('question_text'),
                question_data.get('options'),
                question_data.get('correct_option')
            ]):
                self.logger.warning(f"Missing mandatory fields in question: {question_data}")
                return

            # Check for duplicate based on question_text
            existing_question = self.session.query(Question).filter_by(
                question_text=question_data['question_text']
            ).first()
            
            if existing_question:
                self.logger.info(f"Duplicate found. Skipping question: {question_data['question_text']}")
                return

            # Create a new Question instance
            new_question = Question(
                question_text=question_data['question_text'],
                options=json.dumps(question_data['options']),  # Store options as JSON string
                correct_option=question_data['correct_option'],
                subject=question_data.get('subject'),
                sub_subject=question_data.get('sub_subject'),
                difficulty=question_data.get('difficulty'),
                reasoning=question_data.get('reasoning'),
                created_at=datetime.datetime.utcnow(),
                updated_at=datetime.datetime.utcnow()
            )

            # Add the new question to the session
            self.session.add(new_question)
            self.logger.debug(f"Added question to session: {question_data['question_text']}")

        except Exception as e:
            self.logger.error(f"Error ingesting question: {e}")
            raise

    def ingest_bulk(self, json_data: str):
        """
        Ingest multiple MCQs from a JSON string into the PostgreSQL database using bulk insertion.

        Parameters:
        - json_data (str): JSON string containing the MCQs.

        Returns:
        - None
        """
        try:
            # Parse the JSON data
            data = json.loads(json_data)
            questions = data.get('questions', [])

            if not questions:
                self.logger.warning("No questions found in the provided JSON data.")
                return

            new_questions = []
            ingested_count = 0
            duplicate_count = 0
            incomplete_count = 0

            for q in questions:
                # Extract question details
                question_text = q.get('question')
                options = q.get('options')
                correct_answer = q.get('correct_answer')
                reasoning = q.get('reasoning')
                subject = q.get('subject')
                sub_subject = q.get('sub_subject')  # Optional
                difficulty = q.get('difficulty')    # Optional

                # Check for mandatory fields
                if not all([question_text, options, correct_answer, subject]):
                    self.logger.warning(f"Missing mandatory fields in question: {q}")
                    incomplete_count += 1
                    continue  # Skip incomplete questions

                # Check for duplicate based on question_text
                existing_question = self.session.query(Question).filter_by(question_text=question_text).first()
                if existing_question:
                    self.logger.info(f"Duplicate found. Skipping question: {question_text}")
                    duplicate_count += 1
                    continue  # Skip duplicate

                # Create a new Question instance
                new_question = Question(
                    question_text=question_text,
                    options=json.dumps(options),  # Store options as JSON string
                    correct_option=correct_answer,
                    subject=subject,
                    sub_subject=sub_subject,
                    difficulty=difficulty,
                    reasoning=reasoning,
                    created_at=datetime.datetime.utcnow(),
                    updated_at=datetime.datetime.utcnow()
                )

                new_questions.append(new_question)
                ingested_count += 1

                # Bulk insert in batches
                if len(new_questions) >= self.batch_size:
                    self.session.bulk_save_objects(new_questions)
                    self.session.commit()
                    self.logger.info(f"Ingested {len(new_questions)} questions in bulk.")
                    new_questions = []

            # Insert any remaining questions
            if new_questions:
                self.session.bulk_save_objects(new_questions)
                self.session.commit()
                self.logger.info(f"Ingested {len(new_questions)} questions in bulk.")

            self.logger.info(f"Bulk ingestion completed. Total ingested: {ingested_count}, Duplicates skipped: {duplicate_count}, Incomplete skipped: {incomplete_count}")

        except json.JSONDecodeError as jde:
            self.logger.error(f"JSON decoding failed: {jde}")
        except SQLAlchemyError as sae:
            self.session.rollback()
            self.logger.error(f"Database error occurred: {sae}")
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"An unexpected error occurred: {e}")



#Example script usage

# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker
# from models import Base  # Assuming your models are in models.py

# # Database configuration
# DATABASE_URL = "postgresql+psycopg2://username:password@localhost:5432/your_database"

# # Create the SQLAlchemy engine
# engine = create_engine(DATABASE_URL)

# # Create all tables (if they don't exist)
# Base.metadata.create_all(engine)

# # Create a configured "Session" class
# SessionLocal = sessionmaker(bind=engine)

# # Create a Session
# session = SessionLocal()
