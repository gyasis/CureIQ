# main.py
import json
import logging
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from models import Base, UserPerformance, Question
import datetime
from session import SessionManager

def setup_logging():
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("session.log"),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger()
    return logger

def get_available_subjects(session):
    """Get list of unique subjects from the database."""
    subjects = session.query(Question.subject).distinct().all()
    return [subject[0] for subject in subjects if subject[0]]

def get_review_questions_count(session):
    """Get count of questions due for review."""
    now = datetime.datetime.utcnow()
    return session.query(UserPerformance).filter(
        UserPerformance.next_review <= now
    ).count()

def get_session_parameters(session):
    """
    Interactively get session parameters from user.
    
    Returns:
    - dict: Session parameters
    """
    print("\n" + "="*50)
    print("Study Session Configuration")
    print("="*50)

    # Get available subjects
    subjects = get_available_subjects(session)
    review_count = get_review_questions_count(session)

    # Display session options
    print("\nSession Types:")
    print("1. Review Session (Questions due for review)")
    print("2. Subject-focused Session")
    print("3. Mixed Session (Random questions)")
    print(f"\nYou have {review_count} questions due for review.")

    while True:
        try:
            session_type = int(input("\nSelect session type (1-3): "))
            if 1 <= session_type <= 3:
                break
            print("Please enter a number between 1 and 3.")
        except ValueError:
            print("Please enter a valid number.")

    # Get subject if needed
    subject_filter = None
    if session_type == 2:
        print("\nAvailable subjects:")
        for i, subject in enumerate(subjects, 1):
            print(f"{i}. {subject}")
        
        while True:
            try:
                subject_idx = int(input("\nSelect subject number (0 for all): "))
                if 0 <= subject_idx <= len(subjects):
                    subject_filter = subjects[subject_idx-1] if subject_idx > 0 else None
                    break
                print(f"Please enter a number between 0 and {len(subjects)}.")
            except ValueError:
                print("Please enter a valid number.")

    # Get number of questions
    while True:
        try:
            num_questions = int(input("\nNumber of questions (default 10): ") or "10")
            if num_questions > 0:
                break
            print("Please enter a positive number.")
        except ValueError:
            print("Please enter a valid number.")

    # Determine if random selection should be used
    random_selection = session_type == 3

    return {
        'session_type': session_type,
        'subject': subject_filter,
        'num_questions': num_questions,
        'random_selection': random_selection
    }

def get_previous_sessions(session):
    """
    Get a list of previous study sessions from the database.
    Returns dates of sessions based on UserPerformance last_seen dates.
    """
    # Include the ordering column in the SELECT DISTINCT clause
    sessions = session.query(
        func.date(UserPerformance.last_seen).label('session_date')
    ).distinct().order_by(
        func.date(UserPerformance.last_seen).desc()
    ).limit(10).all()
    
    return [session[0] for session in sessions if session[0]]

def display_previous_session(session, session_date):
    """
    Display the report for a specific session date with detailed performance metrics.
    """
    # Get all questions answered on that date
    questions = session.query(UserPerformance).filter(
        func.date(UserPerformance.last_seen) == session_date
    ).all()

    # Compile session statistics
    stats = {
        'total_questions': len(questions),
        'correct_answers': sum(1 for q in questions if q.times_correct > 0),
        'total_time': sum(q.average_response_time for q in questions),
        'by_subject': {},
        'by_rank': {
            'easy': {'count': 0, 'correct': 0},    # rank < 0.5
            'medium': {'count': 0, 'correct': 0},  # 0.5 <= rank < 1.5
            'hard': {'count': 0, 'correct': 0}     # rank >= 1.5
        },
        'questions_data': []
    }

    # Compile detailed statistics
    for q in questions:
        subject = q.question.subject
        if subject not in stats['by_subject']:
            stats['by_subject'][subject] = {
                'total': 0,
                'correct': 0,
                'times': [],
                'ranks': [],
                'total_attempts': 0,
                'total_correct': 0
            }
        
        # Update subject statistics
        stats['by_subject'][subject]['total'] += 1
        stats['by_subject'][subject]['correct'] += 1 if q.times_correct > 0 else 0
        stats['by_subject'][subject]['times'].append(q.average_response_time)
        stats['by_subject'][subject]['ranks'].append(q.current_rank)
        
        # Track total attempts and correct answers
        stats['by_subject'][subject]['total_attempts'] += (q.times_correct + q.times_incorrect)
        stats['by_subject'][subject]['total_correct'] += q.times_correct

        # Categorize by rank
        if q.current_rank < 0.5:
            stats['by_rank']['easy']['count'] += 1
            stats['by_rank']['easy']['correct'] += 1 if q.times_correct > 0 else 0
        elif q.current_rank < 1.5:
            stats['by_rank']['medium']['count'] += 1
            stats['by_rank']['medium']['correct'] += 1 if q.times_correct > 0 else 0
        else:
            stats['by_rank']['hard']['count'] += 1
            stats['by_rank']['hard']['correct'] += 1 if q.times_correct > 0 else 0

        # Store individual question data
        stats['questions_data'].append({
            'subject': subject,
            'question': q.question.question_text,
            'correct': q.times_correct > 0,
            'response_time': q.average_response_time,
            'rank': q.current_rank,
            'times_seen': q.times_seen,
            'times_correct': q.times_correct,
            'times_incorrect': q.times_incorrect,
            'success_rate': success_rate
        })

    # Display the report
    print("\n" + "="*50)
    print(f"SESSION REPORT FOR {session_date}")
    print("="*50)

    # Overall Performance
    overall_accuracy = (stats['correct_answers'] / stats['total_questions']) * 100
    avg_response_time = stats['total_time'] / stats['total_questions']
    print(f"\nOVERALL PERFORMANCE:")
    print(f"Total Questions: {stats['total_questions']}")
    print(f"Correct Answers: {stats['correct_answers']}")
    print(f"Accuracy: {overall_accuracy:.1f}%")
    print(f"Average Response Time: {avg_response_time:.1f} seconds")

    # Performance by Difficulty (Rank)
    print("\nPERFORMANCE BY DIFFICULTY:")
    for difficulty, data in stats['by_rank'].items():
        if data['count'] > 0:
            accuracy = (data['correct'] / data['count']) * 100
            print(f"\n{difficulty.upper()} Questions:")
            print(f"Count: {data['count']}")
            print(f"Correct: {data['correct']}")
            print(f"Accuracy: {accuracy:.1f}%")

    # Subject Performance
    print("\nPERFORMANCE BY SUBJECT:")
    for subject, data in stats['by_subject'].items():
        avg_rank = sum(data['ranks']) / len(data['ranks'])
        avg_time = sum(data['times']) / len(data['times'])
        session_accuracy = (data['correct'] / data['total']) * 100
        
        # Calculate historical accuracy (across all attempts)
        historical_accuracy = (
            (data['total_correct'] / data['total_attempts'] * 100)
            if data['total_attempts'] > 0 else 0
        )
        
        print(f"\n{subject}:")
        print(f"Questions: {data['total']}")
        print(f"Session Accuracy: {session_accuracy:.1f}%")
        print(f"Historical Accuracy: {historical_accuracy:.1f}%")
        print(f"Average Rank: {avg_rank:.2f}")
        print(f"Average Response Time: {avg_time:.1f} seconds")
        print(f"Total Times Seen: {data['total_attempts']}")

    # Identify Areas for Improvement
    print("\nAREAS FOR IMPROVEMENT:")
    struggling_subjects = [
        (subject, data) for subject, data in stats['by_subject'].items()
        if (data['correct'] / data['total'] * 100) < 80 or  # Session accuracy below 80%
        (data['total_correct'] / data['total_attempts'] * 100 < 80 if data['total_attempts'] > 0 else False) or  # Historical accuracy below 80%
        (sum(data['ranks']) / len(data['ranks'])) > 1.2  # High average rank
    ]
    
    if struggling_subjects:
        for subject, data in struggling_subjects:
            session_accuracy = (data['correct'] / data['total']) * 100
            historical_accuracy = (
                (data['total_correct'] / data['total_attempts'] * 100)
                if data['total_attempts'] > 0 else 0
            )
            avg_rank = sum(data['ranks']) / len(data['ranks'])
            
            print(f"\n{subject}:")
            print(f"Session Accuracy: {session_accuracy:.1f}%")
            print(f"Historical Accuracy: {historical_accuracy:.1f}%")
            print(f"Average Rank: {avg_rank:.2f}")
            print("Recommended: More practice needed to reach 80% accuracy target")
    else:
        print("All subjects are performing above 80% accuracy threshold.")

    print("\n" + "="*50)

def main_menu():
    """Display main menu and get user choice."""
    print("\n" + "="*50)
    print("Study Session Application")
    print("="*50)
    print("\n1. Start New Session")
    print("2. View Previous Session Reports")
    print("3. Exit")
    
    while True:
        try:
            choice = int(input("\nSelect an option (1-3): "))
            if 1 <= choice <= 3:
                return choice
            print("Please enter a number between 1 and 3.")
        except ValueError:
            print("Please enter a valid number.")

def main():
    # Setup logging
    logger = setup_logging()
    logger.info("Starting Study Session Application")

    # Database configuration
    DATABASE_URL = "postgresql+psycopg2://postgresUser:postgresPW@localhost:5455/postgresDB"

    # Create the SQLAlchemy engine
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        while True:
            choice = main_menu()

            if choice == 1:
                # Start new session
                params = get_session_parameters(session)
                session_manager = SessionManager(
                    session=session,
                    max_response_time=60,
                    max_days=30,
                    weight_correct=1.0,
                    weight_response_time=0.5,
                    weight_time=0.5,
                    weight_rank=0.1,
                    weight_trend=2.0
                )

                if params['session_type'] == 1:
                    params['random_selection'] = False
                    logger.info("Starting review session")
                else:
                    logger.info(f"Starting {'random' if params['random_selection'] else 'targeted'} session")

                session_manager.start_session(
                    num_questions=params['num_questions'],
                    subject=params['subject'],
                    sub_subject=None,
                    random_selection=params['random_selection']
                )

            elif choice == 2:
                # View previous sessions
                previous_sessions = get_previous_sessions(session)
                if not previous_sessions:
                    print("\nNo previous sessions found.")
                    continue

                print("\nPrevious Sessions:")
                for i, session_date in enumerate(previous_sessions, 1):
                    print(f"{i}. {session_date}")

                while True:
                    try:
                        session_choice = int(input("\nSelect session to view (0 to cancel): "))
                        if session_choice == 0:
                            break
                        if 1 <= session_choice <= len(previous_sessions):
                            display_previous_session(session, previous_sessions[session_choice-1])
                            break
                        print(f"Please enter a number between 0 and {len(previous_sessions)}.")
                    except ValueError:
                        print("Please enter a valid number.")

            else:  # choice == 3
                print("\nThank you for using the Study Session Application!")
                break

    except Exception as e:
        logger.error(f"An error occurred during the session: {e}")
    finally:
        session.close()
        logger.info("Study Session Application Ended")

if __name__ == "__main__":
    main()
