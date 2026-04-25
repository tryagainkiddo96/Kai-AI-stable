"""
Hermes-inspired cross-session recall system with FTS5 search.
Provides intelligent memory search and summarization across conversations.
"""

import sqlite3
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import re


@dataclass
class MemoryFragment:
    """A searchable memory fragment from conversations"""
    id: str
    session_id: str
    timestamp: str
    user_input: str
    kai_response: str
    context: str = ""
    tags: List[str] = field(default_factory=list)
    importance_score: float = 1.0
    learned_insights: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'timestamp': self.timestamp,
            'user_input': self.user_input,
            'kai_response': self.kai_response,
            'context': self.context,
            'tags': ','.join(self.tags),  # SQLite FTS5 works better with comma-separated
            'importance_score': self.importance_score,
            'learned_insights': json.dumps(self.learned_insights)
        }


class KaiMemorySearch:
    """
    Hermes-inspired cross-session memory with FTS5 search and LLM summarization.
    Provides intelligent recall across all past conversations.
    """

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.db_path = workspace / "memory_search.db"
        self._init_database()

    def _init_database(self):
        """Initialize the FTS5 search database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Create virtual FTS5 table for full-text search
            cursor.execute('''
                CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
                    id, session_id, timestamp, user_input, kai_response, context, tags,
                    importance_score, learned_insights,
                    tokenize = 'porter unicode61'
                )
            ''')

            # Create metadata table for additional queries
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS memory_metadata (
                    id TEXT PRIMARY KEY,
                    session_id TEXT,
                    timestamp TEXT,
                    importance_score REAL,
                    tags TEXT,
                    learned_insights TEXT
                )
            ''')

            # Create indexes for performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_session ON memory_metadata(session_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON memory_metadata(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_importance ON memory_metadata(importance_score)')

            conn.commit()

    def store_memory(self, memory: MemoryFragment):
        """Store a memory fragment in the search database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Prepare data for FTS5 table
            fts_data = memory.to_dict()

            # Insert into FTS5 table
            cursor.execute('''
                INSERT OR REPLACE INTO memory_fts
                (id, session_id, timestamp, user_input, kai_response, context, tags, importance_score, learned_insights)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                fts_data['id'], fts_data['session_id'], fts_data['timestamp'],
                fts_data['user_input'], fts_data['kai_response'], fts_data['context'],
                fts_data['tags'], fts_data['importance_score'], fts_data['learned_insights']
            ))

            # Insert into metadata table
            cursor.execute('''
                INSERT OR REPLACE INTO memory_metadata
                (id, session_id, timestamp, importance_score, tags, learned_insights)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                memory.id, memory.session_id, memory.timestamp,
                memory.importance_score, ','.join(memory.tags),
                json.dumps(memory.learned_insights)
            ))

            conn.commit()

    def search_memories(self, query: str, limit: int = 10, days_back: int = 30) -> List[Dict]:
        """
        Search memories using FTS5 full-text search
        Returns results with relevance scores
        """
        cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # FTS5 search with ranking
            cursor.execute('''
                SELECT
                    m.*,
                    highlight(memory_fts, 3, '<mark>', '</mark>') as highlighted_input,
                    highlight(memory_fts, 4, '<mark>', '</mark>') as highlighted_response,
                    bm25(memory_fts) as relevance_score
                FROM memory_fts m
                WHERE memory_fts MATCH ?
                  AND timestamp > ?
                ORDER BY bm25(memory_fts), importance_score DESC
                LIMIT ?
            ''', (query, cutoff_date, limit))

            results = []
            for row in cursor.fetchall():
                result = {
                    'id': row[0],
                    'session_id': row[1],
                    'timestamp': row[2],
                    'user_input': row[3],
                    'kai_response': row[4],
                    'context': row[5],
                    'tags': row[6].split(',') if row[6] else [],
                    'importance_score': row[7],
                    'learned_insights': json.loads(row[8]) if row[8] else [],
                    'highlighted_input': row[9] or row[3],
                    'highlighted_response': row[10] or row[4],
                    'relevance_score': row[11]
                }
                results.append(result)

            return results

    def search_by_pattern(self, user_pattern: str = None, kai_pattern: str = None,
                         tags: List[str] = None, limit: int = 10) -> List[Dict]:
        """Search memories by specific patterns and tags"""
        conditions = []
        params = []

        if user_pattern:
            conditions.append("user_input LIKE ?")
            params.append(f"%{user_pattern}%")

        if kai_pattern:
            conditions.append("kai_response LIKE ?")
            params.append(f"%{kai_pattern}%")

        if tags:
            tag_conditions = []
            for tag in tags:
                tag_conditions.append("tags LIKE ?")
                params.append(f"%{tag}%")
            if tag_conditions:
                conditions.append("(" + " OR ".join(tag_conditions) + ")")

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        params.extend([limit])

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(f'''
                SELECT m.*, mm.tags, mm.learned_insights
                FROM memory_fts m
                JOIN memory_metadata mm ON m.id = mm.id
                WHERE {where_clause}
                ORDER BY m.timestamp DESC, m.importance_score DESC
                LIMIT ?
            ''', params)

            results = []
            for row in cursor.fetchall():
                results.append({
                    'id': row[0],
                    'session_id': row[1],
                    'timestamp': row[2],
                    'user_input': row[3],
                    'kai_response': row[4],
                    'context': row[5],
                    'tags': row[6].split(',') if row[6] else [],
                    'importance_score': row[7],
                    'learned_insights': json.loads(row[8]) if row[8] else []
                })

            return results

    def get_similar_conversations(self, current_context: str, limit: int = 5) -> List[Dict]:
        """Find conversations similar to current context"""
        # Extract keywords from current context
        keywords = self._extract_keywords(current_context)

        if not keywords:
            return []

        # Search for conversations containing these keywords
        keyword_query = ' OR '.join(keywords)
        return self.search_memories(keyword_query, limit=limit, days_back=90)

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from text"""
        # Remove common stop words and punctuation
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                     'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
                     'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
                     'should', 'may', 'might', 'must', 'can', 'i', 'you', 'he', 'she',
                     'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'}

        words = re.findall(r'\b\w+\b', text.lower())
        keywords = [word for word in words if len(word) > 2 and word not in stop_words]

        # Return top keywords by frequency
        from collections import Counter
        word_counts = Counter(keywords)
        return [word for word, count in word_counts.most_common(5)]

    def get_conversation_insights(self, days_back: int = 30) -> Dict[str, Any]:
        """Get insights about conversation patterns and learning"""
        cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Get basic statistics
            cursor.execute('''
                SELECT COUNT(*), AVG(importance_score),
                       COUNT(DISTINCT session_id)
                FROM memory_metadata
                WHERE timestamp > ?
            ''', (cutoff_date,))

            stats = cursor.fetchone()
            total_memories = stats[0] if stats else 0
            avg_importance = stats[1] if stats and stats[1] else 0.0
            unique_sessions = stats[2] if stats and stats[2] else 0

            # Get most common tags
            cursor.execute('''
                SELECT tags, COUNT(*) as count
                FROM memory_metadata
                WHERE timestamp > ? AND tags != ''
                GROUP BY tags
                ORDER BY count DESC
                LIMIT 10
            ''', (cutoff_date,))

            common_tags = [{'tag': row[0], 'count': row[1]} for row in cursor.fetchall()]

            # Get learning insights
            cursor.execute('''
                SELECT learned_insights
                FROM memory_metadata
                WHERE timestamp > ? AND learned_insights != '[]'
                ORDER BY timestamp DESC
                LIMIT 20
            ''', (cutoff_date,))

            insights = []
            for row in cursor.fetchall():
                try:
                    insight_list = json.loads(row[0])
                    insights.extend(insight_list)
                except:
                    pass

            # Remove duplicates and get top insights
            insight_counts = {}
            for insight in insights:
                insight_counts[insight] = insight_counts.get(insight, 0) + 1

            top_insights = sorted(insight_counts.items(), key=lambda x: x[1], reverse=True)[:5]

            return {
                'period_days': days_back,
                'total_memories': total_memories,
                'average_importance': round(avg_importance, 2),
                'unique_sessions': unique_sessions,
                'common_tags': common_tags,
                'top_learned_insights': [{'insight': k, 'frequency': v} for k, v in top_insights]
            }

    def get_memory_summary(self, session_id: str = None) -> Dict[str, Any]:
        """Get a summary of stored memories"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if session_id:
                # Session-specific summary
                cursor.execute('''
                    SELECT COUNT(*), MIN(timestamp), MAX(timestamp),
                           AVG(importance_score)
                    FROM memory_metadata
                    WHERE session_id = ?
                ''', (session_id,))

                result = cursor.fetchone()
                if result and result[0] > 0:
                    return {
                        'session_id': session_id,
                        'memory_count': result[0],
                        'first_memory': result[1],
                        'last_memory': result[2],
                        'avg_importance': round(result[3] or 0, 2)
                    }
                else:
                    return {'session_id': session_id, 'message': 'No memories found'}
            else:
                # Global summary
                cursor.execute('''
                    SELECT COUNT(*), COUNT(DISTINCT session_id),
                           MIN(timestamp), MAX(timestamp),
                           AVG(importance_score)
                    FROM memory_metadata
                ''')

                result = cursor.fetchone()
                return {
                    'total_memories': result[0] if result else 0,
                    'unique_sessions': result[1] if result else 0,
                    'date_range': {
                        'first': result[2] if result else None,
                        'last': result[3] if result else None
                    },
                    'average_importance': round(result[4] or 0, 2)
                }

    def cleanup_old_memories(self, days_to_keep: int = 365):
        """Clean up memories older than specified days"""
        cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Get count before cleanup
            cursor.execute('SELECT COUNT(*) FROM memory_metadata WHERE timestamp < ?',
                         (cutoff_date,))
            old_count = cursor.fetchone()[0]

            # Delete old memories
            cursor.execute('DELETE FROM memory_fts WHERE timestamp < ?', (cutoff_date,))
            cursor.execute('DELETE FROM memory_metadata WHERE timestamp < ?', (cutoff_date,))

            conn.commit()

            return old_count
