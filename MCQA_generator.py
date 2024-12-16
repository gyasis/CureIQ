import json
import logging
from dotenv import load_dotenv
from guidance import models, gen
from icecream import ic
import dspy
from dspy.clients.lm import LM
from dspy import Signature, Assert
import json
from tqdm import tqdm  # Import tqdm for progress tracking
from dspy import Signature, Module, Assert
import re
from dspy.primitives.assertions import assert_transform_module, backtrack_handler
import litellm
litellm.suppress_debug_logging = True

class MedFactsExtractor:
    def __init__(
        self,
        model_name="gpt-4o",
        env_path="/media/gyasis/Blade 15 SSD/Users/gyasi/Google Drive (not syncing)/Collection/chatrepository/.env",
        system_prompt_path="/home/gyasis/.config/fabric/patterns/extract_medical_facts/system.md"
    ):
        """
        Initialize the MedFactsExtractor class.
        :param model_name: The name of the language model to use.
        :param env_path: Path to the .env file for environment variables. Default is ".env".
        :param system_prompt_path: Path to the markdown file containing the system prompt. Default is "system_prompt.md".
        """
        # Configure logging
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
        )
        
        # Load environment variables if path exists
        if env_path:
            load_dotenv(env_path, override=True)
        
        # Initialize the model
        self.lllm = models.LiteLLMCompletion(model_name, echo=False)
        self.system_prompt = None
        
        # Load the system prompt if the file exists
        try:
            self.system_prompt = self.load_markdown_file(system_prompt_path)
            self.lllm += self.system_prompt
        except FileNotFoundError:
            logging.warning(f"System prompt file not found at: {system_prompt_path}")
    
    @staticmethod
    def load_markdown_file(file_path):
        """Load the contents of a markdown file into a variable."""
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    
    def process_text_to_facts(self, text_corpus):
        """
        Process input text into JSON-encoded facts using the LLM.
        :param text_corpus: The input text to be processed.
        :return: JSON string of extracted facts.
        """
        if not self.system_prompt:
            raise ValueError("System prompt is not loaded. Provide a valid prompt file path.")

        # Add input text to the model
        self.lllm += f"The following is the text to convert into facts: {text_corpus}. Output only the facts, no other text." + gen(name="facts")
        
        # Extract the generated facts
        facts = self.lllm["facts"]
        ic(facts)
        
        # Parse the facts into JSON format
        facts_list = facts.split('\n')
        facts_json = []
        
        for fact in facts_list:
            if fact.strip():  # Ensure the fact is not empty
                subject_start = fact.find('(') + 1
                subject_end = fact.find(')')
                subject = fact[subject_start:subject_end]
                fact_text = fact[subject_end + 2:]  # Skip the closing parenthesis and space
                
                facts_json.append({
                    "subject": subject,
                    "fact": fact_text
                })
        
        # Return the JSON string
        return json.dumps(facts_json, indent=4)

class MCQSignature(Signature):
    """Generate a USMLE style MCQA and right answer reasoning from a given text. 
    Answers should be plain text without any letter designations (A, B, C, D)."""
    text = dspy.InputField(desc="The text(subject) to generate MCQs from.")
    questions = dspy.OutputField(desc="The generated MCQs in JSON format. Options should not include letter prefixes.")

class MCQModule(Module):
    def __init__(self, model_name="openai/gpt-4o-mini", max_tokens=1000):
        super().__init__()
        
        # Configure the language model
        turbo = dspy.LM(model_name, max_tokens=max_tokens)
        dspy.configure(lm=turbo)
        
        # Configure backtracking parameters
        dspy.settings.configure(backtrack_handler=backtrack_handler)
        
        self.prog = dspy.Predict(MCQSignature)

    def normalize_json_structure(self, questions_json):
        """Normalize the JSON structure to ensure consistent format"""
        if 'questions' not in questions_json:
            # If the response is a single question, wrap it in a questions array
            questions_json = {'questions': [questions_json]}
        
        for question in questions_json['questions']:
            # Convert 'answer' to 'correct_answer' if needed
            if 'answer' in question and 'correct_answer' not in question:
                question['correct_answer'] = question.pop('answer')
            
            # Ensure all required keys exist
            required_keys = {'question', 'options', 'correct_answer', 'subject'}
            for key in required_keys:
                if key not in question:
                    if key == 'subject':
                        # Subject will be added later in forward()
                        continue
                    print(f"Missing required key: {key}")
                    question[key] = ''  # Add empty placeholder

        return questions_json

    def forward(self, text):
        response = self.prog(text=text)
        try:
            questions_json = json.loads(response.questions)
            
            # Extract subject from input text
            subject = text.split('Subject: ')[1].split('.')[0] if 'Subject: ' in text else ''
            
            # Add subject to each question in the array
            for question in questions_json.get('questions', []):
                question['subject'] = subject
            
            # Continue with normal processing
            self.normalize_json_structure(questions_json)
            self.clean_options(questions_json)
            self.validate_json_structure(questions_json)
            return questions_json
        except json.JSONDecodeError:
            print("Failed to decode JSON. Please check the output format.")
            return {}

    def clean_options(self, questions_json):
        """Clean options and correct answer of letter designators"""
        for question in questions_json.get('questions', []):
            # Clean options
            cleaned_options = [re.sub(r'^[A-D]\.\s*', '', option.strip()) for option in question.get('options', [])]
            question['options'] = cleaned_options
            
            # Clean correct answer
            if 'correct_answer' in question:
                question['correct_answer'] = re.sub(r'^[A-D]\.\s*', '', question['correct_answer'].strip())

    def validate_json_structure(self, questions_json):
        # Update validation to include subject
        if not isinstance(questions_json, dict) or 'questions' not in questions_json:
            print("Invalid top-level JSON structure. Expected a dictionary with a 'questions' key.")
            return False

        questions = questions_json['questions']
        def is_valid_structure(questions):
            for question in questions:
                if not isinstance(question, dict):
                    print(f"Invalid question format: {question}")
                    return False
                # Add 'subject' to required keys
                required_keys = {'question', 'options', 'correct_answer', 'subject'}
                for key in required_keys:
                    if key not in question:
                        print(f"Missing '{key}' key in: {question}")
                        return False
            return True

        is_valid = is_valid_structure(questions)
        print(f"Validation result: {is_valid}")
        Assert(is_valid, "Invalid JSON structure for questions", target_module="MCQModule")

def main():
    # Create an instance of the module with assertions
    mcq_module = assert_transform_module(MCQModule())

    # Initialize the class with default paths
    extractor = MedFactsExtractor()

    # Input text
    text_corpus = input("Enter the text to convert into facts:")

    # Convert to JSON
    json_output = extractor.process_text_to_facts(text_corpus)

    # Output the result
    print(json_output)

    # Parse the JSON string into a Python list of dictionaries
    facts_list = json.loads(json_output)

    # Process each fact to generate MCQs
    all_questions = []  # List to store all questions
    for fact in tqdm(facts_list, desc="Generating MCQs"):
        # Combine subject and fact for input text
        input_text = f"Subject: {fact['subject']}. Fact: {fact['fact']}"
        print(f"Input text: {input_text}")  # Log the input text
        
        # Generate MCQs
        response = mcq_module.forward(input_text)
        
        # Extract questions from response and add to all_questions list
        if 'questions' in response:
            all_questions.extend(response['questions'])
        
        # Output the generated MCQs in JSON format
        print(json.dumps(response, indent=4))

    # Create final response structure
    final_response = {'questions': all_questions}

    # Save all responses to a JSON file
    with open('mcq_responses.json', 'w') as json_file:
        json.dump(final_response, json_file, indent=4)

if __name__ == "__main__":
    main()