import sqlite3
from pathlib import Path

from app.core.config import settings


DEFAULT_CONVERSATION_TITLE = "默认会话"


class ConversationMemory:
    def __init__(self, db_path: str, max_messages: int = 20):
        self.db_path = Path(db_path)
        self.max_messages = max_messages
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                )
                """
            )
            self._ensure_messages_conversation_id(connection)
            default_conversation_id = self._ensure_default_conversation(connection)
            connection.execute(
                "UPDATE messages SET conversation_id = ? WHERE conversation_id IS NULL",
                (default_conversation_id,),
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_messages_conversation_id
                ON messages (conversation_id, id)
                """
            )

    def _ensure_messages_conversation_id(self, connection: sqlite3.Connection) -> None:
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(messages)").fetchall()
        }
        if "conversation_id" not in columns:
            connection.execute("ALTER TABLE messages ADD COLUMN conversation_id INTEGER")

    def _ensure_default_conversation(self, connection: sqlite3.Connection) -> int:
        row = connection.execute(
            "SELECT id FROM conversations ORDER BY id ASC LIMIT 1"
        ).fetchone()
        if row:
            return int(row["id"])

        cursor = connection.execute(
            "INSERT INTO conversations (title) VALUES (?)",
            (DEFAULT_CONVERSATION_TITLE,),
        )
        return int(cursor.lastrowid)

    def _row_to_conversation(self, row: sqlite3.Row) -> dict[str, str | int]:
        return {
            "id": row["id"],
            "title": row["title"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def create_conversation(self, title: str | None = None) -> dict[str, str | int]:
        conversation_title = (title or "新会话").strip() or "新会话"
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO conversations (title) VALUES (?)",
                (conversation_title,),
            )
            row = connection.execute(
                "SELECT id, title, created_at, updated_at FROM conversations WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()

        return self._row_to_conversation(row)

    def update_conversation_title(
        self,
        conversation_id: int,
        title: str,
    ) -> dict[str, str | int] | None:
        conversation_title = title.strip()
        if not conversation_title:
            return None

        with self._connect() as connection:
            connection.execute(
                """
                UPDATE conversations
                SET title = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (conversation_title[:80], conversation_id),
            )
            row = connection.execute(
                "SELECT id, title, created_at, updated_at FROM conversations WHERE id = ?",
                (conversation_id,),
            ).fetchone()

        return self._row_to_conversation(row) if row else None

    def delete_conversation(self, conversation_id: int) -> bool:
        with self._connect() as connection:
            conversation = connection.execute(
                "SELECT id FROM conversations WHERE id = ?",
                (conversation_id,),
            ).fetchone()
            if not conversation:
                return False

            connection.execute(
                "DELETE FROM messages WHERE conversation_id = ?",
                (conversation_id,),
            )
            connection.execute(
                "DELETE FROM conversations WHERE id = ?",
                (conversation_id,),
            )
            return True

    def get_default_conversation_id(self) -> int:
        with self._connect() as connection:
            return self._ensure_default_conversation(connection)

    def get_conversation(self, conversation_id: int) -> dict[str, str | int] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, title, created_at, updated_at
                FROM conversations
                WHERE id = ?
                """,
                (conversation_id,),
            ).fetchone()

        return self._row_to_conversation(row) if row else None

    def list_conversations(self) -> list[dict[str, str | int]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, title, created_at, updated_at
                FROM conversations
                ORDER BY updated_at DESC, id DESC
                """
            ).fetchall()

        return [self._row_to_conversation(row) for row in rows]

    def _touch_conversation(self, connection: sqlite3.Connection, conversation_id: int) -> None:
        connection.execute(
            "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (conversation_id,),
        )

    def _maybe_update_title(
        self,
        connection: sqlite3.Connection,
        conversation_id: int,
        role: str,
        content: str,
    ) -> None:
        if role != "user":
            return

        row = connection.execute(
            "SELECT title FROM conversations WHERE id = ?",
            (conversation_id,),
        ).fetchone()
        if not row or row["title"] not in {"新会话", DEFAULT_CONVERSATION_TITLE}:
            return

        title = content.strip().replace("\n", " ")[:24]
        if title:
            connection.execute(
                "UPDATE conversations SET title = ? WHERE id = ?",
                (title, conversation_id),
            )

    def add_message(self, conversation_id: int, role: str, content: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO messages (conversation_id, role, content)
                VALUES (?, ?, ?)
                """,
                (conversation_id, role, content),
            )
            self._maybe_update_title(connection, conversation_id, role, content)
            self._touch_conversation(connection, conversation_id)

    def get_messages(self, conversation_id: int) -> list[dict[str, str]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT role, content
                FROM messages
                WHERE conversation_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (conversation_id, self.max_messages),
            ).fetchall()

        return [
            {
                "role": row["role"],
                "content": row["content"],
            }
            for row in reversed(rows)
        ]

    def get_history(self, conversation_id: int) -> list[dict[str, str]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT role, content, created_at
                FROM messages
                WHERE conversation_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (conversation_id, self.max_messages),
            ).fetchall()

        return [
            {
                "role": row["role"],
                "content": row["content"],
                "created_at": row["created_at"],
            }
            for row in reversed(rows)
        ]

    def clear(self, conversation_id: int) -> None:
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM messages WHERE conversation_id = ?",
                (conversation_id,),
            )
            self._touch_conversation(connection, conversation_id)


conversation_memory = ConversationMemory(
    db_path=settings.memory_db_path,
)
