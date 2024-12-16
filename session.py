# session.py (Complete SessionManager class with updated present_question method)

import json
import datetime
import logging
import time
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from models import Question, UserPerformance
import random

class SessionManager:
    def __init__(self, session: Session, max_response_time=60, max_days=30,
                 weight_correct=1.0, weight_response_time=0.5, weight_time=0.5, weight_rank=0.1, weight_trend=2.0):
        """
        Initialize the SessionManager with parameters for scoring.

        Parameters:
        - session (Session): SQLAlchemy session object connected to the database.
        - max_response_time (int): Maximum response time in seconds for normalization.
        - max_days (int): Maximum days to consider for time since last review.
        - weight_correct (float): Weight for correctness factor.
        - weight_response_time (float): Weight for response time factor.
        - weight_time (float): Weight for time since last review factor.
        - weight_rank (float): Weight for current rank factor.
        - weight_trend (float): Weight for trend factor.
        """
        self.session = session
        self.max_response_time = max_response_time
        self.max_days = max_days
        self.weight_correct = weight_correct
        self.weight_response_time = weight_response_time
        self.weight_time = weight_time
        self.weight_rank = weight_rank
        self.weight_trend = weight_trend
        self.logger = logging.getLogger(self.__class__.__name__)

    def calculate_score(self, perf: UserPerformance):
        """
        Calculate the priority score for a question based on performance.
        Lower scores indicate higher priority.

        Parameters:
        - perf (UserPerformance): The user's performance record for the question.

        Returns:
        - float: Calculated score.
        """
        # Calculate time since last review in days
        if perf.last_seen:
            time_since_last_review = (datetime.datetime.utcnow() - perf.last_seen).total_seconds() / 86400  # Convert to days
        else:
            time_since_last_review = self.max_days  # New questions have highest priority

        # Normalize factors
        times_correct = perf.times_correct
        times_incorrect = perf.times_incorrect
        avg_response_time = perf.average_response_time
        time_since_last_review = min(time_since_last_review, self.max_days)

        # Correctness factor: More correct answers lower the score
        correctness_factor = 1 / (times_correct + 1)

        # Response time factor: Faster responses lower the score
        response_time_factor = avg_response_time / self.max_response_time

        # Time factor: More time since last review lowers the score
        time_factor = time_since_last_review / self.max_days

        # Rank factor: Higher rank increases the score
        rank_factor = perf.current_rank

        # **Trend Factor Calculation**
        if perf.times_seen > 1 and perf.previous_times_correct > 0:
            current_correctness = times_correct / perf.times_seen
            previous_correctness = perf.previous_times_correct / (perf.times_seen - 1)
            change_correctness = current_correctness - previous_correctness
        else:
            change_correctness = 0  # No previous data to compare

        if perf.times_seen > 1 and perf.previous_average_response_time > 0:
            change_response_time = (perf.previous_average_response_time - avg_response_time) / (perf.previous_average_response_time + 1)
        else:
            change_response_time = 0  # No previous data to compare

        trend_factor = change_correctness + change_response_time

        # Calculate total score
        score = (correctness_factor * self.weight_correct +
                 response_time_factor * self.weight_response_time +
                 time_factor * self.weight_time -
                 (rank_factor * self.weight_rank) +
                 (trend_factor * self.weight_trend))

        return score

    def select_questions(self, num_questions=20, subject=None, sub_subject=None, random_selection=False):
        """
        Select a set of questions based on the scoring algorithm.

        Parameters:
        - num_questions (int): Number of questions to select.
        - subject (str): Subject filter.
        - sub_subject (str): Sub-subject filter.
        - random_selection (bool): If True, select questions randomly without scoring.

        Returns:
        - list of Question: Selected questions for the session.
        """
        query = self.session.query(Question)

        # Apply subject filters if specified
        if subject:
            query = query.filter(Question.subject.ilike(f"%{subject}%"))
        if sub_subject:
            query = query.filter(Question.sub_subject.ilike(f"%{sub_subject}%"))

        # Join with UserPerformance
        query = query.outerjoin(UserPerformance).options()

        questions = query.all()

        scored_questions = []
        for q in questions:
            if q.performance:
                score = self.calculate_score(q.performance)
            else:
                # If the question has never been seen, prioritize it
                score = 0  # Highest priority
            scored_questions.append((q, score))

        if random_selection:
            # Shuffle and select randomly
            random.shuffle(scored_questions)
            selected = [q for q, s in scored_questions[:num_questions]]
        else:
            # Sort by score ascending and pick top N
            scored_questions.sort(key=lambda x: x[1])
            selected = [q for q, s in scored_questions[:num_questions]]

        self.logger.info(f"Selected {len(selected)} questions for the session.")
        return selected

    def present_question(self, question: Question):
        """
        Present a question to the user with randomized options and collect their answer.

        Parameters:
        - question (Question): The question to present.

        Returns:
        - tuple: (is_correct (bool), response_time (float))
        """
        print("\n" + "="*50)
        print("\nQuestion:")
        print(question.question_text)
        print("\nOptions:")

        # Parse options from JSON string if necessary
        try:
            if isinstance(question.options, str):
                # Remove any surrounding quotes and clean the string
                cleaned_options = question.options.strip('"\'')
                # Try parsing as JSON
                try:
                    options = json.loads(cleaned_options)
                except json.JSONDecodeError:
                    # If JSON parsing fails, try splitting by comma
                    options = [opt.strip() for opt in cleaned_options.split(',') if opt.strip()]
            else:
                options = question.options

            if not isinstance(options, list):
                options = list(options)

        except Exception as e:
            self.logger.error(f"Failed to parse options: {question.options}. Error: {e}")
            options = []  # Fallback to empty list

        # Create a copy of the parsed options list
        shuffled_options = options.copy()
        random.shuffle(shuffled_options)  # Shuffle in place

        # Assign labels to options
        option_labels = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']  # Support more options if needed
        labeled_options = list(zip(option_labels[:len(shuffled_options)], shuffled_options))

        # Display shuffled options with labels
        for label, option in labeled_options:
            print(f"  {label}. {option.strip().strip('"\'[]\\')}")
        
        # Collect user answer with response time
        start_time = time.time()
        user_input = input("\nEnter the option letter (e.g., A): ").strip().upper()
        end_time = time.time()
        response_time = end_time - start_time

        # Validate user input
        valid_labels = [label for label, _ in labeled_options]
        if user_input not in valid_labels:
            print("Invalid option selected. Please try again.")
            return self.present_question(question)  # Retry the same question

        # Retrieve the selected option based on user input
        selected_option = dict(labeled_options).get(user_input)
        selected_option = selected_option.strip().strip('"\'[]\\')
        correct_option = question.correct_option.strip().strip('"\'[]\\')
        is_correct = (selected_option == correct_option)

        if is_correct:
            print("✅ Correct!")
        else:
            print(f"❌ Incorrect. The correct answer is: {correct_option}")

        print(f"Response Time: {response_time:.2f} seconds")
        return is_correct, response_time

    def update_performance(self, question: Question, is_correct: bool, response_time: float):
        """
        Update the UserPerformance record based on the user's answer.

        Parameters:
        - question (Question): The question that was answered.
        - is_correct (bool): Whether the user's answer was correct.
        - response_time (float): Time taken by the user to answer in seconds.

        Returns:
        - None
        """
        try:
            perf = self.session.query(UserPerformance).filter_by(question_id=question.id).first()
            now = datetime.datetime.utcnow()
            
            if not perf:
                # New question - calculate initial interval
                interval = self.calculate_interval(1.0, correct=is_correct, is_new=True)
                initial_rank = 0.8 if is_correct else 1.2  # Adjust initial rank based on first answer
                
                perf = UserPerformance(
                    question_id=question.id,
                    last_seen=now,
                    times_seen=1,
                    times_correct=1 if is_correct else 0,
                    times_incorrect=0 if is_correct else 1,
                    average_response_time=response_time,
                    next_review=now + datetime.timedelta(days=interval),
                    current_rank=initial_rank,
                    previous_times_correct=0,
                    previous_average_response_time=0.0
                )
                self.session.add(perf)
                self.logger.debug(f"Created new UserPerformance for question ID {question.id}")
            else:
                # Update previous performance metrics
                perf.previous_times_correct = perf.times_correct
                perf.previous_average_response_time = perf.average_response_time

                # Update current performance metrics
                perf.last_seen = now
                perf.times_seen += 1
                if is_correct:
                    perf.times_correct += 1
                else:
                    perf.times_incorrect += 1

                # Update average response time with weighted average
                perf.average_response_time = (
                    (perf.average_response_time * (perf.times_seen - 1) + response_time) / 
                    perf.times_seen
                )

                # Calculate performance trend
                correctness_ratio = perf.times_correct / perf.times_seen
                response_time_improvement = (
                    (perf.previous_average_response_time - perf.average_response_time) / 
                    perf.previous_average_response_time if perf.previous_average_response_time > 0 else 0
                )

                # Update rank based on performance
                rank_adjustment = 0.1  # Base adjustment value
                if is_correct:
                    # Decrease rank (improve) based on performance
                    rank_adjustment *= (1 + correctness_ratio + response_time_improvement)
                    perf.current_rank = max(0.1, perf.current_rank - rank_adjustment)
                else:
                    # Increase rank (deteriorate) based on performance
                    rank_adjustment *= (2 - correctness_ratio)
                    perf.current_rank = min(2.0, perf.current_rank + rank_adjustment)

                # Calculate next review interval
                interval = self.calculate_interval(perf.current_rank, correct=is_correct)
                perf.next_review = now + datetime.timedelta(days=interval)

                self.logger.debug(f"Updated UserPerformance for question ID {question.id}")
            
            self.session.commit()
            self.logger.info(f"Updated performance for question ID {question.id}")
            
            # Log detailed performance metrics
            self.logger.debug(
                f"Performance metrics for question {question.id}: "
                f"Rank={perf.current_rank:.2f}, "
                f"Next review in {interval} days, "
                f"Correct ratio={perf.times_correct/perf.times_seen:.2%}"
            )
            
        except SQLAlchemyError as sae:
            self.session.rollback()
            self.logger.error(f"Database error occurred while updating performance: {sae}")
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"An unexpected error occurred while updating performance: {e}")

    def calculate_interval(self, current_rank, correct=True, is_new=False):
        """
        Calculate the next interval based on current rank, correctness, and whether it's a new question.

        Parameters:
        - current_rank (float): Current rank of the question.
        - correct (bool): Whether the answer was correct.
        - is_new (bool): Whether this is a new question.

        Returns:
        - int: Number of days until the next review.
        """
        base_interval = 1  # Start with 1 day
        
        if is_new:
            return 3 if correct else 1
        
        if correct:
            # Exponential increase for correct answers
            interval = base_interval * (2 ** (current_rank))
        else:
            # Shorter interval for incorrect answers
            interval = base_interval / (current_rank)
        
        return max(1, int(interval))  # At least 1 day

    def start_session(self, num_questions=20, subject=None, sub_subject=None, random_selection=False):
        """
        Start a study session by selecting questions, presenting them, and updating metrics.

        Parameters:
        - num_questions (int): Number of questions in the session.
        - subject (str): Subject filter.
        - sub_subject (str): Sub-subject filter.
        - random_selection (bool): If True, select questions randomly without scoring.

        Returns:
        - None
        """
        selected_questions = self.select_questions(
            num_questions=num_questions,
            subject=subject,
            sub_subject=sub_subject,
            random_selection=random_selection
        )

        if not selected_questions:
            print("No questions available for the session based on the current parameters.")
            return

        print(f"\nStarting a session with {len(selected_questions)} questions.\n")
        
        # Initialize session statistics
        session_stats = {
            'total_questions': len(selected_questions),
            'correct_answers': 0,
            'total_time': 0,
            'by_subject': {},
            'questions_data': []
        }

        for idx, question in enumerate(selected_questions, 1):
            print(f"Question {idx}/{len(selected_questions)}:")
            is_correct, response_time = self.present_question(question)
            self.update_performance(question, is_correct, response_time)

            # Update session statistics
            session_stats['correct_answers'] += int(is_correct)
            session_stats['total_time'] += response_time
            
            # Update subject-specific statistics
            subject = question.subject
            if subject not in session_stats['by_subject']:
                session_stats['by_subject'][subject] = {
                    'total': 0,
                    'correct': 0,
                    'times': []
                }
            
            session_stats['by_subject'][subject]['total'] += 1
            session_stats['by_subject'][subject]['correct'] += int(is_correct)
            session_stats['by_subject'][subject]['times'].append(response_time)

            # Store question data
            session_stats['questions_data'].append({
                'subject': subject,
                'question': question.question_text,
                'correct': is_correct,
                'response_time': response_time
            })

        # Generate and display session report
        self._display_session_report(session_stats)

    def _display_session_report(self, stats):
        """
        Display a detailed report of the study session.
        
        Parameters:
        - stats (dict): Session statistics
        """
        print("\n" + "="*50)
        print("SESSION SUMMARY")
        print("="*50)

        # Overall Performance
        overall_accuracy = (stats['correct_answers'] / stats['total_questions']) * 100
        avg_response_time = stats['total_time'] / stats['total_questions']
        
        print(f"\nOverall Performance:")
        print(f"Total Questions: {stats['total_questions']}")
        print(f"Correct Answers: {stats['correct_answers']}")
        print(f"Accuracy: {overall_accuracy:.1f}%")
        print(f"Average Response Time: {avg_response_time:.1f} seconds")

        # Performance by Subject
        print("\nPerformance by Subject:")
        print("-" * 40)
        
        # Sort subjects by performance (descending)
        subject_performance = []
        for subject, data in stats['by_subject'].items():
            accuracy = (data['correct'] / data['total']) * 100
            avg_time = sum(data['times']) / len(data['times'])
            subject_performance.append((subject, accuracy, avg_time, data['total']))
        
        # Sort by accuracy (descending)
        subject_performance.sort(key=lambda x: x[1], reverse=True)

        # Display subject performance
        print("\nStrong Subjects (>= 70% accuracy):")
        print("-" * 40)
        for subject, accuracy, avg_time, total in subject_performance:
            if accuracy >= 70:
                print(f"{subject}:")
                print(f"  Accuracy: {accuracy:.1f}%")
                print(f"  Average Response Time: {avg_time:.1f} seconds")
                print(f"  Questions Attempted: {total}")

        print("\nSubjects Needing Improvement (< 70% accuracy):")
        print("-" * 40)
        for subject, accuracy, avg_time, total in subject_performance:
            if accuracy < 70:
                print(f"{subject}:")
                print(f"  Accuracy: {accuracy:.1f}%")
                print(f"  Average Response Time: {avg_time:.1f} seconds")
                print(f"  Questions Attempted: {total}")

        # Detailed Question Analysis
        print("\nDetailed Question Analysis:")
        print("-" * 40)
        incorrect_questions = [q for q in stats['questions_data'] if not q['correct']]
        if incorrect_questions:
            print("\nQuestions to Review:")
            for q in incorrect_questions:
                print(f"\nSubject: {q['subject']}")
                print(f"Question: {q['question']}")
                print(f"Response Time: {q['response_time']:.1f} seconds")
        
        print("\n" + "="*50)
