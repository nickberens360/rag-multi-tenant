#!/usr/bin/env python3
"""
Migration script to populate database with hardcoded followup questions.
This script will create categories and questions based on the hardcoded values in followup_service.py
"""

import logging
import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from core.admin_database import admin_db_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_hardcoded_questions() -> bool:
    """Migrate hardcoded questions to the database.

    Returns:
        bool: True on success, False on error.
    """

    # Hardcoded question pools from followup_service.py
    question_pools = {
        "technical": {
            "display_name": "Technical",
            "description": "Questions about development, technologies, and technical expertise",
            "icon": "code-tags",
            "questions": [
                "What technologies do you work with?",
                "Tell me about your development philosophy?",
                "Show me your coding projects",
                "What frameworks do you prefer?",
                "How do you approach problem solving?",
            ],
        },
        "personal": {
            "display_name": "Personal",
            "description": "Questions about background, experience, and personal journey",
            "icon": "account",
            "questions": [
                "Tell me about your experience",
                "What's your background?",
                "How can I contact Nick?",
                "What motivates you?",
                "Tell me about your journey",
            ],
        },
        "creative": {
            "display_name": "Creative",
            "description": "Questions about artistic work, illustrations, and creative process",
            "icon": "palette",
            "questions": [
                "Show me your illustrations",
                "What inspires your artwork?",
                "Tell me about your creative process",
                "Show me your design work",
                "What art styles do you enjoy?",
            ],
        },
    }

    try:
        logger.info("Starting migration of hardcoded followup questions to database...")

        # Check if categories already exist
        existing_categories = admin_db_manager.get_followup_categories(active_only=False)
        existing_category_names = {cat["name"] for cat in existing_categories}

        categories_created = 0
        questions_created = 0

        for category_name, category_data in question_pools.items():
            logger.info(f"Processing category: {category_name}")

            # Check if category already exists
            if category_name in existing_category_names:
                logger.info(f"Category '{category_name}' already exists, getting existing category...")
                category = next(cat for cat in existing_categories if cat["name"] == category_name)
                category_id = category["id"]

                # Check if category has questions
                existing_questions = admin_db_manager.get_followup_questions(category_id=category_id, active_only=False)
                existing_question_texts = {q["question_text"] for q in existing_questions}

                if len(existing_questions) >= len(category_data["questions"]):
                    logger.info(
                        f"Category '{category_name}' already has {len(existing_questions)} questions (expected {len(category_data['questions'])}), checking for completeness..."
                    )
                    # Check if we have all expected questions
                    missing_questions = set(category_data["questions"]) - existing_question_texts
                    if not missing_questions:
                        logger.info(f"Category '{category_name}' already has all expected questions, skipping...")
                        continue
                    else:
                        logger.info(
                            f"Category '{category_name}' is missing {len(missing_questions)} questions, will add them"
                        )
                else:
                    logger.info(
                        f"Category '{category_name}' has {len(existing_questions)} questions but needs {len(category_data['questions'])}, will add missing ones"
                    )
            else:
                # Create new category
                logger.info(f"Creating new category: {category_name}")
                category_id = admin_db_manager.create_followup_category(
                    name=category_name,
                    display_name=category_data["display_name"],
                    description=category_data["description"],
                    icon=category_data["icon"],
                    sort_order=list(question_pools.keys()).index(category_name),
                )

                if not category_id:
                    logger.error(f"Failed to create category: {category_name}")
                    continue

                categories_created += 1
                logger.info(f"Created category '{category_name}' with ID: {category_id}")

            # Add questions to the category (only missing ones if category exists)
            if category_name in existing_category_names:
                questions_to_add = [q for q in category_data["questions"] if q not in existing_question_texts]
            else:
                questions_to_add = category_data["questions"]

            for i, question_text in enumerate(questions_to_add):
                logger.info(f"Adding question: {question_text}")

                # Calculate sort_order based on existing questions + new position
                if category_name in existing_category_names:
                    sort_order = len(existing_questions) + i
                else:
                    sort_order = category_data["questions"].index(question_text)

                question_id = admin_db_manager.create_followup_question(
                    category_id=category_id,
                    question_text=question_text,
                    sort_order=sort_order,
                    created_by=None,  # System migration
                )

                if question_id:
                    questions_created += 1
                    logger.info(f"Created question with ID: {question_id}")
                else:
                    logger.error(f"Failed to create question: {question_text}")

        logger.info(f"Migration completed successfully!")
        logger.info(f"Categories created: {categories_created}")
        logger.info(f"Questions created: {questions_created}")

        # Verify the migration
        final_categories = admin_db_manager.get_followup_categories(active_only=False)
        total_questions = sum(admin_db_manager.get_category_question_count(cat["id"]) for cat in final_categories)

        logger.info(
            f"Final verification - Total categories: {len(final_categories)}, Total questions: {total_questions}"
        )

        return True

    except Exception as e:
        logger.error(f"Migration failed: {str(e)}", exc_info=True)
        return False


def rollback_migration():
    """Rollback migration by deleting all categories and questions."""
    try:
        logger.info("Rolling back migration...")

        categories = admin_db_manager.get_followup_categories(active_only=False)
        for category in categories:
            if category["name"] in ["technical", "personal", "creative"]:
                logger.info(f"Deleting category: {category['name']}")
                admin_db_manager.delete_followup_category(category["id"])

        logger.info("Rollback completed successfully!")
        return True

    except Exception as e:
        logger.error(f"Rollback failed: {str(e)}", exc_info=True)
        return False


def main():
    """Main function to run migration or rollback."""
    if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
        success = rollback_migration()
    else:
        success = migrate_hardcoded_questions()

    if success:
        logger.info("Operation completed successfully!")
        sys.exit(0)
    else:
        logger.error("Operation failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
