import jsonlines
import json
import uuid
import datetime
from datetime import UTC  # Import UTC for timezone-aware datetime


class MCQDataProcessor:
    def __init__(self, input_data):
        """
        Initialize the processor with raw MCQ data.
        :param input_data: Dictionary containing MCQ questions and metadata.
        """
        self.input_data = input_data

    def generate_unique_id(self):
        """
        Generate a unique 12-character alphanumeric ID.
        :return: A 12-character unique ID string.
        """
        return uuid.uuid4().hex[:12]

    def extract_relevant_data(self):
        processed_data = []
        current_time = datetime.datetime.now(UTC).isoformat()  # Convert to ISO format string
        
        for question_group in self.input_data.get("questions", []):
            processed_question = {
                "question_text": question_group.get("question"),
                "options": json.dumps(question_group.get("options", [])),  # Store as JSON string
                "correct_option": question_group.get("correct_answer"),
                "subject": question_group.get("subject"),
                "sub_subject": question_group.get("sub_subject", None),  # Optional
                "difficulty": question_group.get("difficulty", None),  # Optional
                "reasoning": question_group.get("reasoning", None),  # Optional
                "created_at": current_time,
                "updated_at": current_time
            }
            processed_data.append(processed_question)
        return processed_data

    def save_to_jsonl(self, output_file):
        """
        Save the processed data to a JSONL file.
        :param output_file: Path to the output JSONL file.
        """
        relevant_data = self.extract_relevant_data()
        with jsonlines.open(output_file, mode='w') as writer:
            writer.write_all(relevant_data)

# Example Usage
if __name__ == "__main__":
    # Replace `raw_data` with your actual MCQ data dictionary
    raw_data = json.load(open("mcq_responses.json"))

    processor = MCQDataProcessor(raw_data)
    processor.save_to_jsonl("processed_mcq_data.jsonl")
