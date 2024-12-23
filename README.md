# CureIQ 
## MCQA Ingestion and Generation System

## Overview

This project is designed to facilitate the ingestion, generation, and processing of multiple-choice questions (MCQs) for educational purposes. It leverages a combination of natural language processing (NLP) and database management to create a robust system for handling MCQs. The point is to grab questions from a text corpus and store them in a database for later use.

## Components

### 1. Collector (`collector.py`)

The `Collector` class integrates the functionality of generating, processing, and ingesting MCQs. It takes a text corpus, generates MCQs, processes them, and ingests them into a database for later use.

- **Initialization**: 
  - `database_url`: The database connection URL.
  - `model_name`: The name of the language model to use (default is "gpt-4o").
  - `env_path`: Path to the `.env` file for environment variables.
  - `system_prompt_path`: Path to the markdown file containing the system prompt.

- **Methods**:
  - `process_and_ingest(text_corpus)`: Processes the text corpus to generate MCQs and ingests them into the database.

### 2. Ingest (`ingest.py`)

The `Ingest` class handles the ingestion of MCQs into a PostgreSQL database using SQLAlchemy. It supports both single and bulk ingestion methods.

- **Methods**:
  - `ingest_single(json_data)`: Ingests a single MCQ from a JSON string into the database.
  - `ingest_bulk(json_data)`: Ingests multiple MCQs from a JSON string into the database using bulk insertion.

### 3. MCQ Generator (`MCQA_generator.py`)

This module uses a language model to extract facts from text and generate MCQs. It processes input text to produce JSON-encoded facts and then generates questions based on these facts.

- **Classes**:
  - `MedFactsExtractor`: Extracts medical facts from a text corpus.
  - `MCQModule`: Generates MCQs from extracted facts.

### 4. MCQ Processor (`MCQA_processor.py`)

The `MCQDataProcessor` class processes raw MCQ data, assigns unique IDs, and saves the processed data to a JSONL file for further use.

- **Methods**:
  - `extract_relevant_data()`: Extracts relevant parts of the MCQ data.
  - `save_to_jsonl(output_file)`: Saves the processed data to a JSONL file.

### 5. Data Models (`models.py`)

Defines the database schema for storing questions and user performance data using SQLAlchemy ORM.

- **Classes**:
  - `Question`: Represents the questions table in the database.
  - `UserPerformance`: Represents the user performance table in the database.

### 6. Main Application (`main.py`)

Sets up the application environment, including logging and database connections, and manages study sessions using a `SessionManager`.

- **Functions**:
  - `setup_logging()`: Configures logging for the application.
  - `main()`: Starts a study session with specified parameters.

## Setup and Usage

### Prerequisites

- Python 3.8+
- PostgreSQL database
- Required Python packages (listed in `requirements.txt`)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/gyasis/mcq-system.git
   cd mcq-system
   ```

2. Configure your database connection in `main.py` and `collector.py` by setting the `DATABASE_URL`.

### Using the Collector

1. **Initialize the Collector**: Create an instance of the `Collector` class with the appropriate database URL and optional parameters for the language model.

2. **Process and Ingest Text Corpus**: Use the `process_and_ingest` method to convert a text corpus into MCQs and store them in the database.

   ```python
   collector = Collector(DATABASE_URL)
   text_corpus = "Enter your text corpus here."
   collector.process_and_ingest(text_corpus)
   ```

### Running a Study Session

1. **Setup Logging**: Ensure logging is configured in `main.py`.

2. **Start a Session**: Execute `main.py` to start a study session, which will select questions from the database based on specified criteria.

   ```bash
   python main.py
   ```

### Logging

Logs are saved to `session.log` and can be configured in `main.py`.

### Database
We utilize PostgreSQL as our primary database solution for several compelling reasons:

1. **Vector and Graph Capabilities:**

    PostgreSQL supports advanced data types and indexing techniques that are essential for handling vector-based data and graph relationships efficiently. This makes it an excellent choice for applications that require complex querying and data relationships.

2. **Reliability and Performance:**

    Known for its robustness, PostgreSQL ensures data integrity and consistency. Its performance optimization features allow for handling large volumes of data with minimal latency.

3. **Extensibility:**

    PostgreSQL's extensible nature allows us to incorporate custom functions and extensions tailored to our project's specific needs, enhancing functionality without compromising on performance.

4. **Community and Support:**

    With a strong open-source community, PostgreSQL benefits from continuous improvements, security updates, and a wealth of resources that aid in troubleshooting and development.

By leveraging PostgreSQL's powerful features, we ensure that all information is stored securely and can be accessed and manipulated efficiently, supporting both our current and future data management requirements.

## Roadmap

### Phase 1: Web-Based Frontend Development (Current)
- Develop a React/Next.js web application frontend
- Implement user authentication and session management
- Create interactive question viewing and answering interface
- Add progress tracking and performance analytics dashboard
- Design responsive layouts for mobile and desktop
- Integrate REST API endpoints with the backend

### Phase 2: Vector Search Implementation
- Integrate vector embeddings for questions and answers
- Add semantic search capabilities for similar questions
- Implement efficient question retrieval based on content similarity
- Enable context-aware question recommendations
- Create search filters and advanced query options

### Phase 3: Smart Question Management
- Develop intelligent question editing interface
- Add bulk question modification capabilities
- Implement version control for question edits
- Create question quality metrics and filtering
- Add automated question validation
- Build collaborative editing features

### ~~Phase 4: Multimodal Question Generation~~
- ~~Integrate OCR capabilities for image-based content~~
- ~~Support question generation from diagrams and charts~~
- ~~Add image-based question types~~
- ~~Implement multi-format content processing~~
- ~~Support PDF and document parsing~~
- ~~Create visual question builder interface~~

### Phase 5: AI Tutoring System
- Develop specialized tutor agents for different subjects
- Implement adaptive learning paths
- Create personalized difficulty scaling
- Add real-time explanation generation
- Develop concept mapping and prerequisite tracking
- Implement intelligent review scheduling
- Build interactive tutoring interface

Each phase will be developed iteratively with continuous integration of user feedback and performance metrics.

## Recent Updates

### 12/22/2024
- **Multimodal Input Support**: Added the ability to process images and extract text using the `ImageCaptureGateway`. This allows users to upload images, which are processed to extract text and generate MCQs.
- **Web Server Option**: Introduced the `--web` command-line option to run a FastAPI server, enabling continuous processing of text and images. This server allows users to upload images or input text directly through a web interface.
- **ImageProcessor Integration**: Integrated the `ImageProcessor` class to handle image processing tasks, utilizing the `MediaBatchProcessor` for extracting text from images.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request for any improvements or bug fixes.

## License

This project is licensed under the MIT License.

