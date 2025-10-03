"""
Unified service for managing categories and questions with ACID guarantees.
This service provides transactional operations for follow-up question management.
"""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from .db_session import get_db_session_sync

logger = logging.getLogger(__name__)


class FollowUpManagementService:
    """Unified service for managing categories and questions with ACID guarantees."""

    def __init__(self):
        pass

    def delete_category_with_strategy(
        self, category_id: int, strategy: str, target_category_id: Optional[int] = None, user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Delete category with explicit handling of dependent questions.

        Args:
            category_id: ID of category to delete
            strategy: 'move', 'delete', or 'deactivate'
            target_category_id: Required for 'move' strategy
            user_id: User performing the operation

        Returns:
            Dictionary with operation results

        Strategies:
        - 'move': Move questions to target category
        - 'delete': Delete questions permanently
        - 'deactivate': Soft delete category, preserve questions
        """
        try:
            with get_db_session_sync() as session:
                if session is None:
                    raise RuntimeError("Database unavailable")

                # Validate category exists and get question count
                row = session.execute(
                    text("SELECT id, name, display_name, is_active FROM followup_categories WHERE id = :id"),
                    {"id": category_id},
                ).first()
                if not row:
                    raise ValueError(f"Category {category_id} not found")
                category = {"id": row[0], "name": row[1], "display_name": row[2], "is_active": bool(row[3])}

                question_count = (
                    session.execute(
                        text("SELECT COUNT(*) FROM followup_questions WHERE category_id = :id"), {"id": category_id}
                    ).scalar()
                    or 0
                )

                if strategy == "move" and question_count > 0:
                    if not target_category_id:
                        raise ValueError("Target category required for move strategy")
                    tgt = session.execute(
                        text("SELECT id, is_active FROM followup_categories WHERE id = :id"),
                        {"id": target_category_id},
                    ).first()
                    if not tgt or not bool(tgt[1]):
                        raise ValueError("Invalid target category")
                    res = session.execute(
                        text("UPDATE followup_questions SET category_id = :tgt WHERE category_id = :src"),
                        {"tgt": target_category_id, "src": category_id},
                    )
                    logger.info(f"Moved {res.rowcount or 0} questions to category {target_category_id}")

                elif strategy == "delete" and question_count > 0:
                    res = session.execute(
                        text("DELETE FROM followup_questions WHERE category_id = :id"), {"id": category_id}
                    )
                    logger.info(f"Deleted {res.rowcount or 0} questions from category {category_id}")

                elif strategy == "deactivate":
                    res = session.execute(
                        text("UPDATE followup_categories SET is_active = false, updated_at = now() WHERE id = :id"),
                        {"id": category_id},
                    )
                    if (res.rowcount or 0) == 0:
                        raise ValueError("Failed to deactivate category")
                    return {
                        "success": True,
                        "action": "deactivated",
                        "questions_preserved": question_count,
                        "category_name": category["display_name"],
                    }

                if strategy in ["move", "delete"]:
                    res = session.execute(text("DELETE FROM followup_categories WHERE id = :id"), {"id": category_id})
                    if (res.rowcount or 0) == 0:
                        raise ValueError("Failed to delete category")

                return {
                    "success": True,
                    "action": strategy,
                    "questions_affected": question_count,
                    "target_category_id": target_category_id if strategy == "move" else None,
                    "category_name": category["display_name"],
                }

        except Exception as e:
            # SECURITY FIX: Transaction automatically rolls back on exception with context manager
            logger.error(f"Error deleting category {category_id}: {str(e)}")
            raise

    def bulk_update_questions(self, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Perform bulk operations on questions.

        Args:
            operations: List of operation dictionaries with 'action', 'question_id', etc.

        Returns:
            Dictionary with results summary
        """
        try:
            with get_db_session_sync() as session:
                if session is None:
                    raise RuntimeError("Database unavailable")

                results: Dict[str, Any] = {
                    "success": True,
                    "operations_completed": 0,
                    "operations_failed": 0,
                    "errors": [],
                }

                for operation in operations:
                    try:
                        action = operation.get("action")
                        question_id = operation.get("question_id")

                        if action == "delete":
                            res = session.execute(
                                text("DELETE FROM followup_questions WHERE id = :id"), {"id": question_id}
                            )
                            success = (res.rowcount or 0) > 0
                        elif action == "activate":
                            res = session.execute(
                                text("UPDATE followup_questions SET is_active = true WHERE id = :id"),
                                {"id": question_id},
                            )
                            success = (res.rowcount or 0) > 0
                        elif action == "deactivate":
                            res = session.execute(
                                text("UPDATE followup_questions SET is_active = false WHERE id = :id"),
                                {"id": question_id},
                            )
                            success = (res.rowcount or 0) > 0
                        elif action == "update":
                            res = session.execute(
                                text(
                                    "UPDATE followup_questions SET question_text = COALESCE(:qt, question_text), sort_order = COALESCE(:so, sort_order), updated_at = now() WHERE id = :id"
                                ),
                                {
                                    "qt": operation.get("question_text"),
                                    "so": operation.get("sort_order"),
                                    "id": question_id,
                                },
                            )
                            success = (res.rowcount or 0) > 0
                        else:
                            raise ValueError(f"Unknown action: {action}")

                        if success:
                            results["operations_completed"] += 1
                        else:
                            results["operations_failed"] += 1
                            results["errors"].append(f"Operation failed for question {question_id}")

                    except Exception as e:
                        results["operations_failed"] += 1
                        results["errors"].append(f"Error in operation: {str(e)}")

                return results

        except Exception as e:
            # SECURITY FIX: Transaction automatically rolls back with context manager
            logger.error(f"Error in bulk operations: {str(e)}")
            raise

    def reorder_questions_in_category(self, category_id: int, question_orders: List[Dict[str, int]]) -> bool:
        """
        Reorder questions within a category.

        Args:
            category_id: Category to reorder questions in
            question_orders: List of {question_id, sort_order} dictionaries
        """
        try:
            with get_db_session_sync() as session:
                if session is None:
                    return False
                for item in question_orders:
                    session.execute(
                        text(
                            "UPDATE followup_questions SET sort_order = :so, updated_at = now() WHERE id = :qid AND category_id = :cid"
                        ),
                        {"so": item["sort_order"], "qid": item["question_id"], "cid": category_id},
                    )
                logger.info(f"Reordered {len(question_orders)} questions in category {category_id}")
                return True

        except Exception as e:
            # SECURITY FIX: Transaction automatically rolls back with context manager
            logger.error(f"Error reordering questions: {str(e)}")
            return False

    def get_category_with_questions(self, category_id: int) -> Optional[Dict[str, Any]]:
        """Get category with its questions included."""
        try:
            with get_db_session_sync() as session:
                if session is None:
                    return None
                row = session.execute(
                    text(
                        "SELECT id, name, display_name, description, icon, sort_order, is_active, created_at, updated_at FROM followup_categories WHERE id = :id"
                    ),
                    {"id": category_id},
                ).first()
                if not row:
                    return None
                category = {
                    "id": int(row[0]),
                    "name": row[1],
                    "display_name": row[2],
                    "description": row[3],
                    "icon": row[4],
                    "sort_order": row[5],
                    "is_active": bool(row[6]),
                    "created_at": row[7],
                    "updated_at": row[8],
                }
                qrows = session.execute(
                    text(
                        "SELECT id, question_text, sort_order, is_active, created_at, updated_at FROM followup_questions WHERE category_id = :id ORDER BY sort_order, id"
                    ),
                    {"id": category_id},
                ).fetchall()
                questions = [
                    {
                        "id": r[0],
                        "question_text": r[1],
                        "sort_order": r[2],
                        "is_active": bool(r[3]),
                        "created_at": r[4],
                        "updated_at": r[5],
                    }
                    for r in qrows
                ]
                category["questions"] = questions
                category["questions_count"] = len(questions)
                return category
        except Exception as e:
            logger.error(f"Error getting category with questions: {str(e)}")
            return None

    def search_questions(self, query: str, category_id: Optional[int] = None, limit: int = 20) -> List[Dict]:
        """Full-text search across questions."""
        try:
            with get_db_session_sync() as session:
                if session is None:
                    return []
                if category_id:
                    rows = session.execute(
                        text(
                            """
                            SELECT id, category_id, question_text, sort_order, is_active, created_at, updated_at
                            FROM followup_questions
                            WHERE category_id = :cid AND question_text ILIKE :q
                            ORDER BY sort_order, id
                            LIMIT :limit
                            """
                        ),
                        {"cid": category_id, "q": f"%{query}%", "limit": int(limit)},
                    ).fetchall()
                else:
                    rows = session.execute(
                        text(
                            """
                            SELECT id, category_id, question_text, sort_order, is_active, created_at, updated_at
                            FROM followup_questions
                            WHERE question_text ILIKE :q
                            ORDER BY sort_order, id
                            LIMIT :limit
                            """
                        ),
                        {"q": f"%{query}%", "limit": int(limit)},
                    ).fetchall()
                return [
                    {
                        "id": r[0],
                        "category_id": r[1],
                        "question_text": r[2],
                        "sort_order": r[3],
                        "is_active": bool(r[4]),
                        "created_at": r[5],
                        "updated_at": r[6],
                    }
                    for r in rows
                ]
        except Exception as e:
            logger.error(f"Error searching questions: {str(e)}")
            return []

    def get_categories_with_stats(self) -> List[Dict[str, Any]]:
        """Get all categories with question counts and usage stats."""
        try:
            with get_db_session_sync() as session:
                if session is None:
                    return []
                rows = session.execute(
                    text(
                        "SELECT id, name, display_name, description, icon, sort_order, is_active, created_at, updated_at FROM followup_categories ORDER BY sort_order, id"
                    )
                ).fetchall()
                cats = []
                for r in rows:
                    count = (
                        session.execute(
                            text("SELECT COUNT(*) FROM followup_questions WHERE category_id = :id"), {"id": r[0]}
                        ).scalar()
                        or 0
                    )
                    cats.append(
                        {
                            "id": int(r[0]),
                            "name": r[1],
                            "display_name": r[2],
                            "description": r[3],
                            "icon": r[4],
                            "sort_order": r[5],
                            "is_active": bool(r[6]),
                            "created_at": r[7],
                            "updated_at": r[8],
                            "questions_count": int(count),
                        }
                    )
                return cats
        except Exception as e:
            logger.error(f"Error getting categories with stats: {str(e)}")
            return []

    def validate_category_deletion(self, category_id: int) -> Dict[str, Any]:
        """Validate whether a category can be deleted and provide options.

        Returns a dict that is backward-compatible with callers expecting
        either `can_delete` or `valid` boolean flags.
        """
        try:
            category = self.db_manager.get_followup_category(category_id)
            if not category:
                return {"valid": False, "can_delete": False, "error": "Category not found"}

            question_count = self.db_manager.get_category_question_count(category_id)

            # Get available target categories for move operation
            target_categories = [
                cat
                for cat in self.db_manager.get_followup_categories()
                if cat["id"] != category_id and cat.get("is_active", True)
            ]

            result = {
                "valid": True,
                "can_delete": True,  # Backward-compat for older route usage
                "category": category,
                "questions_count": question_count,
                "can_delete_directly": question_count == 0,
                "available_strategies": {
                    "move": len(target_categories) > 0,
                    "delete": True,
                    "deactivate": True,
                },
                "target_categories": target_categories,
            }
            return result
        except Exception as e:
            logger.error(f"Error validating category deletion: {str(e)}")
            return {"valid": False, "can_delete": False, "error": str(e)}


# Global instance
followup_management_service = FollowUpManagementService()
