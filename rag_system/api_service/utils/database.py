"""
Database utilities for RAG System
Handles SQLite operations, schema creation, and data management
"""

import sqlite3
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager
import threading

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Thread-safe SQLite database manager for RAG system"""
    
    def __init__(self, db_path: str = "rag_system/data/metadata.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self.init_database()
        logger.info(f"Database initialized at: {self.db_path}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection"""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                str(self.db_path), 
                check_same_thread=False,
                timeout=30.0
            )
            self._local.connection.row_factory = sqlite3.Row
            # Enable foreign keys
            self._local.connection.execute("PRAGMA foreign_keys = ON")
            # Enable WAL mode for better concurrency
            self._local.connection.execute("PRAGMA journal_mode = WAL")
        
        return self._local.connection
    
    @contextmanager
    def get_cursor(self):
        """Context manager for database operations"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database operation failed: {e}")
            raise
        finally:
            cursor.close()
    
    def init_database(self):
        """Initialize database with required tables"""
        logger.info("Initializing database schema...")
        
        # Main chunks table
        chunks_table = """
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chunk_id TEXT UNIQUE NOT NULL,
            document_id TEXT NOT NULL,
            title TEXT,
            source TEXT,
            version TEXT DEFAULT "1.0",
            language TEXT DEFAULT "vi",
            text TEXT NOT NULL,
            tokens INTEGER,
            heading TEXT,
            heading_level INTEGER DEFAULT 1,
            section_index INTEGER DEFAULT 0,
            section_chunk_index INTEGER DEFAULT 0,
            start_page INTEGER DEFAULT 1,
            end_page INTEGER DEFAULT 1,
            
            -- Soft delete and versioning
            is_active INTEGER DEFAULT 1,
            invalidated_by TEXT DEFAULT NULL,
            
            -- Access control
            access_roles TEXT DEFAULT '["all"]',
            confidentiality_level TEXT DEFAULT 'internal',
            
            -- Metadata
            author TEXT DEFAULT 'Unknown',
            category TEXT DEFAULT 'Uncategorized',
            keywords TEXT DEFAULT '[]',
            summary TEXT DEFAULT '',
            metadata TEXT DEFAULT '{}',
            
            -- Embedding for rebuild capability
            embedding TEXT,
            
            -- Timestamps
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_accessed TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        # Audit log table
        audit_table = """
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_name TEXT NOT NULL,
            record_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            old_values TEXT,
            new_values TEXT,
            user_id TEXT DEFAULT 'system',
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            reason TEXT,
            ip_address TEXT
        );
        """
        
        # Document metadata table
        documents_table = """
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            source TEXT NOT NULL,
            version TEXT DEFAULT "1.0",
            language TEXT DEFAULT "vi",
            author TEXT DEFAULT 'Unknown',
            category TEXT DEFAULT 'Uncategorized',
            total_chunks INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            file_size INTEGER DEFAULT 0,
            file_hash TEXT,
            processing_status TEXT DEFAULT 'pending',
            error_message TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_processed TEXT
        );
        """
        
        # Search analytics table
        search_analytics = """
        CREATE TABLE IF NOT EXISTS search_analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_text TEXT NOT NULL,
            query_embedding_hash TEXT,
            results_count INTEGER,
            top_chunk_ids TEXT,
            search_time_ms INTEGER,
            user_id TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            feedback_score INTEGER DEFAULT NULL,
            session_id TEXT
        );
        """
        
        # Create indexes for performance
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_chunks_active ON chunks(is_active);",
            "CREATE INDEX IF NOT EXISTS idx_chunks_chunk_id ON chunks(chunk_id);",
            "CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);",
            "CREATE INDEX IF NOT EXISTS idx_chunks_version ON chunks(version);",
            "CREATE INDEX IF NOT EXISTS idx_chunks_updated ON chunks(updated_at);",
            "CREATE INDEX IF NOT EXISTS idx_chunks_access_roles ON chunks(access_roles);",
            "CREATE INDEX IF NOT EXISTS idx_documents_document_id ON documents(document_id);",
            "CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(processing_status);",
            "CREATE INDEX IF NOT EXISTS idx_audit_record ON audit_log(table_name, record_id);",
            "CREATE INDEX IF NOT EXISTS idx_search_timestamp ON search_analytics(timestamp);",
        ]
        
        with self.get_cursor() as cursor:
            cursor.execute(chunks_table)
            cursor.execute(audit_table)
            cursor.execute(documents_table)
            cursor.execute(search_analytics)
            
            for index_sql in indexes:
                cursor.execute(index_sql)
        
        logger.info("Database schema initialized successfully")
    
    def insert_chunk(self, chunk_data: Dict[str, Any]) -> int:
        """Insert a new chunk and return its ID"""
        
        # Prepare data with defaults
        chunk_data.setdefault('created_at', datetime.now().isoformat())
        chunk_data.setdefault('updated_at', datetime.now().isoformat())
        
        # Convert lists/dicts to JSON strings
        if 'embedding' in chunk_data and isinstance(chunk_data['embedding'], list):
            chunk_data['embedding'] = json.dumps(chunk_data['embedding'])
        
        if 'access_roles' in chunk_data and isinstance(chunk_data['access_roles'], list):
            chunk_data['access_roles'] = json.dumps(chunk_data['access_roles'])
            
        if 'keywords' in chunk_data and isinstance(chunk_data['keywords'], list):
            chunk_data['keywords'] = json.dumps(chunk_data['keywords'])
            
        if 'metadata' in chunk_data and isinstance(chunk_data['metadata'], dict):
            chunk_data['metadata'] = json.dumps(chunk_data['metadata'])
        
        insert_sql = """
        INSERT INTO chunks (
            chunk_id, document_id, title, source, version, language,
            text, tokens, heading, heading_level, section_index, section_chunk_index,
            start_page, end_page, access_roles, confidentiality_level,
            author, category, keywords, summary, metadata, embedding
        ) VALUES (
            :chunk_id, :document_id, :title, :source, :version, :language,
            :text, :tokens, :heading, :heading_level, :section_index, :section_chunk_index,
            :start_page, :end_page, :access_roles, :confidentiality_level,
            :author, :category, :keywords, :summary, :metadata, :embedding
        )
        """
        
        with self.get_cursor() as cursor:
            cursor.execute(insert_sql, chunk_data)
            chunk_id = cursor.lastrowid
            
            logger.debug(f"Inserted chunk {chunk_data.get('chunk_id')} with ID {chunk_id}")
            return chunk_id
    
    def get_active_chunks(self, document_id: Optional[str] = None) -> List[sqlite3.Row]:
        """Get all active chunks, optionally filtered by document"""
        
        base_sql = """
        SELECT * FROM chunks 
        WHERE is_active = 1 AND invalidated_by IS NULL
        """
        
        params = {}
        if document_id:
            base_sql += " AND document_id = :document_id"
            params['document_id'] = document_id
        
        base_sql += " ORDER BY document_id, section_index, section_chunk_index"
        
        with self.get_cursor() as cursor:
            cursor.execute(base_sql, params)
            return cursor.fetchall()
    
    def get_chunks_by_ids(self, chunk_ids: List[int]) -> Dict[int, sqlite3.Row]:
        """Get chunks by their database IDs"""
        
        if not chunk_ids:
            return {}
        
        placeholders = ','.join(['?' for _ in chunk_ids])
        sql = f"""
        SELECT * FROM chunks 
        WHERE id IN ({placeholders})
        AND is_active = 1 
        AND invalidated_by IS NULL
        """
        
        with self.get_cursor() as cursor:
            cursor.execute(sql, chunk_ids)
            rows = cursor.fetchall()
            return {row['id']: row for row in rows}
    
    def soft_delete_chunk(self, chunk_id: str, invalidated_by: Optional[str] = None, 
                         reason: str = "", user_id: str = "system") -> bool:
        """Soft delete a chunk by marking it inactive"""
        
        with self.get_cursor() as cursor:
            # Get current data for audit
            cursor.execute("SELECT * FROM chunks WHERE chunk_id = ?", (chunk_id,))
            old_data = cursor.fetchone()
            
            if not old_data:
                logger.warning(f"Chunk {chunk_id} not found for deletion")
                return False
            
            # Soft delete
            cursor.execute("""
                UPDATE chunks 
                SET is_active = 0, 
                    invalidated_by = ?, 
                    updated_at = ?
                WHERE chunk_id = ?
            """, (invalidated_by, datetime.now().isoformat(), chunk_id))
            
            # Audit log
            cursor.execute("""
                INSERT INTO audit_log (table_name, record_id, action, old_values, reason, user_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                'chunks', 
                old_data['id'], 
                'SOFT_DELETE',
                json.dumps(dict(old_data)),
                reason,
                user_id
            ))
            
            logger.info(f"Soft deleted chunk {chunk_id}")
            return True
    
    def log_search(self, query_text: str, results_count: int, 
                  search_time_ms: int, top_chunk_ids: List[int],
                  user_id: Optional[str] = None, session_id: Optional[str] = None):
        """Log search analytics"""
        
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO search_analytics (
                    query_text, results_count, top_chunk_ids, 
                    search_time_ms, user_id, session_id
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                query_text,
                results_count, 
                json.dumps(top_chunk_ids),
                search_time_ms,
                user_id,
                session_id
            ))
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        
        with self.get_cursor() as cursor:
            stats = {}
            
            # Chunk statistics
            cursor.execute("SELECT COUNT(*) as total FROM chunks")
            stats['total_chunks'] = cursor.fetchone()['total']
            
            cursor.execute("SELECT COUNT(*) as active FROM chunks WHERE is_active = 1")
            stats['active_chunks'] = cursor.fetchone()['active']
            
            cursor.execute("SELECT COUNT(*) as inactive FROM chunks WHERE is_active = 0")
            stats['inactive_chunks'] = cursor.fetchone()['inactive']
            
            # Document statistics
            cursor.execute("SELECT COUNT(*) as total FROM documents")
            stats['total_documents'] = cursor.fetchone()['total']
            
            # Recent search activity
            cursor.execute("""
                SELECT COUNT(*) as searches 
                FROM search_analytics 
                WHERE timestamp > datetime('now', '-24 hours')
            """)
            stats['searches_last_24h'] = cursor.fetchone()['searches']
            
            # Database size
            cursor.execute("PRAGMA page_count")
            page_count = cursor.fetchone()[0]
            cursor.execute("PRAGMA page_size") 
            page_size = cursor.fetchone()[0]
            stats['database_size_mb'] = round((page_count * page_size) / (1024 * 1024), 2)
            
            return stats
    
    def cleanup_old_logs(self, days: int = 30):
        """Clean up old audit logs and search analytics"""
        
        cutoff_date = datetime.now().isoformat()
        
        with self.get_cursor() as cursor:
            # Clean old audit logs
            cursor.execute("""
                DELETE FROM audit_log 
                WHERE timestamp < datetime('now', '-{} days')
            """.format(days))
            
            # Clean old search analytics
            cursor.execute("""
                DELETE FROM search_analytics 
                WHERE timestamp < datetime('now', '-{} days')
            """.format(days))
            
            logger.info(f"Cleaned up logs older than {days} days")
    
    def close_connections(self):
        """Close all database connections"""
        if hasattr(self._local, 'connection'):
            self._local.connection.close()
            delattr(self._local, 'connection')

# Global database instance
    def backup_database(self, backup_path: Optional[str] = None) -> str:
        """Create database backup"""
        if not backup_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"rag_system/data/backup_metadata_{timestamp}.db"
        
        backup_path = Path(backup_path)
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        
        with self.get_cursor() as cursor:
            # Use SQLite backup API for consistent backup
            backup_conn = sqlite3.connect(str(backup_path))
            self._get_connection().backup(backup_conn)
            backup_conn.close()
        
        logger.info(f"Database backup created: {backup_path}")
        return str(backup_path)
    
    def restore_database(self, backup_path: str):
        """Restore database from backup"""
        backup_path = Path(backup_path)
        
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")
        
        # Close existing connections
        self.close_connections()
        
        # Replace current database
        import shutil
        shutil.copy2(backup_path, self.db_path)
        
        logger.info(f"Database restored from: {backup_path}")
    
    def vacuum_database(self):
        """Vacuum database to reclaim space and optimize"""
        with self.get_cursor() as cursor:
            cursor.execute("VACUUM")
        logger.info("Database vacuumed successfully")
    
    def analyze_database(self):
        """Update database statistics for query optimization"""
        with self.get_cursor() as cursor:
            cursor.execute("ANALYZE")
        logger.info("Database analyzed successfully")

class ChunkFilter:
    """Advanced filtering for chunk queries"""
    
    def __init__(self):
        self.conditions = []
        self.params = {}
        self.param_counter = 0
    
    def add_condition(self, field: str, operator: str, value: Any, 
                     param_name: Optional[str] = None) -> 'ChunkFilter':
        """Add a filter condition"""
        if not param_name:
            param_name = f"param_{self.param_counter}"
            self.param_counter += 1
        
        self.conditions.append(f"{field} {operator} :{param_name}")
        self.params[param_name] = value
        return self
    
    def add_text_search(self, text: str, fields: List[str] = None) -> 'ChunkFilter':
        """Add full-text search condition"""
        if not fields:
            fields = ['text', 'title', 'heading']
        
        search_conditions = []
        for field in fields:
            param_name = f"search_{field}_{self.param_counter}"
            search_conditions.append(f"{field} LIKE :{param_name}")
            self.params[param_name] = f"%{text}%"
            self.param_counter += 1
        
        combined_condition = f"({' OR '.join(search_conditions)})"
        self.conditions.append(combined_condition)
        return self
    
    def add_access_roles(self, user_roles: List[str]) -> 'ChunkFilter':
        """Add access role filtering"""
        if 'all' not in user_roles:
            # Complex JSON filtering for access roles
            role_conditions = []
            for role in user_roles:
                param_name = f"role_{self.param_counter}"
                role_conditions.append(f"access_roles LIKE :{param_name}")
                self.params[param_name] = f'%"{role}"%'
                self.param_counter += 1
            
            if role_conditions:
                combined_roles = f"({' OR '.join(role_conditions)} OR access_roles LIKE '%\"all\"%')"
                self.conditions.append(combined_roles)
        
        return self
    
    def add_date_range(self, start_date: Optional[str] = None, 
                      end_date: Optional[str] = None,
                      field: str = 'updated_at') -> 'ChunkFilter':
        """Add date range filtering"""
        if start_date:
            param_name = f"start_date_{self.param_counter}"
            self.conditions.append(f"{field} >= :{param_name}")
            self.params[param_name] = start_date
            self.param_counter += 1
        
        if end_date:
            param_name = f"end_date_{self.param_counter}"
            self.conditions.append(f"{field} <= :{param_name}")
            self.params[param_name] = end_date
            self.param_counter += 1
        
        return self
    
    def build_query(self, base_query: str) -> Tuple[str, Dict[str, Any]]:
        """Build the final query with all conditions"""
        if self.conditions:
            where_clause = " AND ".join(self.conditions)
            if "WHERE" in base_query.upper():
                query = f"{base_query} AND {where_clause}"
            else:
                query = f"{base_query} WHERE {where_clause}"
        else:
            query = base_query
        
        return query, self.params

class DatabaseQueryBuilder:
    """Advanced query builder for complex database operations"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    # Thay thế hàm cũ trong lớp DatabaseQueryBuilder bằng hàm này

    def search_chunks_advanced(self, 
                            chunk_ids: Optional[List[int]] = None,
                            text_search: Optional[str] = None,
                            document_ids: Optional[List[str]] = None,
                            user_roles: Optional[List[str]] = None,
                            categories: Optional[List[str]] = None,
                            date_from: Optional[str] = None,
                            date_to: Optional[str] = None,
                            limit: int = 100,
                            offset: int = 0,
                            order_by: str = "updated_at DESC") -> List[sqlite3.Row]:
        """Advanced chunk search with multiple filters"""
        
        # Sử dụng filter_builder để xây dựng các điều kiện và tham số một cách an toàn
        base_query = "SELECT * FROM chunks"
        filter_builder = ChunkFilter()

        # Luôn thêm các điều kiện cơ bản
        filter_builder.add_condition("is_active", "=", 1)
        filter_builder.add_condition("invalidated_by", "IS", None)

        # Thêm các bộ lọc tùy chọn
        if chunk_ids:
            # Xử lý an toàn cho danh sách ID
            placeholders = ','.join(['?' for _ in chunk_ids])
            # Thêm trực tiếp vào query string và params vì filter_builder không hỗ trợ tốt
            # Đây là một cách tiếp cận khác, an toàn hơn
            # Chúng ta sẽ xây dựng query mà không dùng filter_builder cho trường hợp này
            
            # Cách tiếp cận đơn giản và đúng đắn nhất
            base_query_simple = "SELECT * FROM chunks"
            conditions = ["is_active = 1", "invalidated_by IS NULL"]
            params = []

            if chunk_ids:
                placeholders = ','.join(['?' for _ in chunk_ids])
                conditions.append(f"id IN ({placeholders})")
                params.extend(chunk_ids)
            
            if document_ids:
                placeholders = ','.join(['?' for _ in document_ids])
                conditions.append(f"document_id IN ({placeholders})")
                params.extend(document_ids)

            if categories:
                placeholders = ','.join(['?' for _ in categories])
                conditions.append(f"category IN ({placeholders})")
                params.extend(categories)
            
            # Nối các điều kiện lại với nhau
            if conditions:
                final_query = f"{base_query_simple} WHERE {' AND '.join(conditions)}"
            else:
                final_query = base_query_simple

            final_query += f" ORDER BY {order_by} LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            # FIX: Thêm khối lệnh thực thi và trả về kết quả
            with self.db.get_cursor() as cursor:
                cursor.execute(final_query, params)
                return cursor.fetchall()
    
    def get_chunk_statistics(self, document_id: Optional[str] = None) -> Dict[str, Any]:
        """Get detailed statistics about chunks"""
        
        base_condition = "WHERE is_active = 1"
        params = {}
        
        if document_id:
            base_condition += " AND document_id = :document_id"
            params['document_id'] = document_id
        
        stats_queries = {
            'total_chunks': f"SELECT COUNT(*) as count FROM chunks {base_condition}",
            'total_tokens': f"SELECT COALESCE(SUM(tokens), 0) as sum FROM chunks {base_condition}",
            'avg_tokens': f"SELECT COALESCE(AVG(tokens), 0) as avg FROM chunks {base_condition}",
            'categories': f"""
                SELECT category, COUNT(*) as count 
                FROM chunks {base_condition}
                GROUP BY category 
                ORDER BY count DESC
            """,
            'languages': f"""
                SELECT language, COUNT(*) as count 
                FROM chunks {base_condition}
                GROUP BY language
            """,
            'recent_updates': f"""
                SELECT DATE(updated_at) as date, COUNT(*) as count
                FROM chunks {base_condition}
                AND updated_at > datetime('now', '-30 days')
                GROUP BY DATE(updated_at)
                ORDER BY date DESC
            """
        }
        
        results = {}
        
        with self.db.get_cursor() as cursor:
            for stat_name, query in stats_queries.items():
                cursor.execute(query, params)
                
                if stat_name in ['categories', 'languages', 'recent_updates']:
                    results[stat_name] = [dict(row) for row in cursor.fetchall()]
                else:
                    row = cursor.fetchone()
                    results[stat_name] = row[0] if row else 0
        
        return results
    
    def cleanup_orphaned_data(self) -> Dict[str, int]:
        """Clean up orphaned and inconsistent data"""
        
        cleanup_results = {
            'orphaned_chunks': 0,
            'duplicate_chunk_ids': 0,
            'invalid_embeddings': 0
        }
        
        with self.db.get_cursor() as cursor:
            # Find orphaned chunks (chunks without valid document references)
            cursor.execute("""
                SELECT COUNT(*) FROM chunks c
                LEFT JOIN documents d ON c.document_id = d.document_id
                WHERE d.document_id IS NULL AND c.is_active = 1
            """)
            cleanup_results['orphaned_chunks'] = cursor.fetchone()[0]
            
            # Find duplicate chunk_ids
            cursor.execute("""
                SELECT chunk_id, COUNT(*) as count
                FROM chunks
                GROUP BY chunk_id
                HAVING COUNT(*) > 1
            """)
            cleanup_results['duplicate_chunk_ids'] = len(cursor.fetchall())
            
            # Find chunks with invalid embedding JSON
            cursor.execute("""
                SELECT COUNT(*) FROM chunks
                WHERE embedding IS NOT NULL 
                AND embedding != ''
                AND json_valid(embedding) = 0
            """)
            cleanup_results['invalid_embeddings'] = cursor.fetchone()[0]
        
        return cleanup_results

# Extended database manager with query builder
class ExtendedDatabaseManager(DatabaseManager):
    """Extended database manager with advanced query capabilities"""
    
    def __init__(self, db_path: str = "rag_system/data/metadata.db"):
        super().__init__(db_path)
        self.query_builder = DatabaseQueryBuilder(self)
    
    def health_check(self) -> Dict[str, Any]:
        """Comprehensive database health check"""
        
        health_status = {
            'status': 'healthy',
            'issues': [],
            'warnings': [],
            'stats': {}
        }
        
        try:
            # Test basic connectivity
            with self.get_cursor() as cursor:
                cursor.execute("SELECT 1")
            
            # Get database stats
            health_status['stats'] = self.get_database_stats()
            
            # Check for issues
            cleanup_stats = self.query_builder.cleanup_orphaned_data()
            
            for issue_type, count in cleanup_stats.items():
                if count > 0:
                    health_status['warnings'].append(f"{issue_type}: {count}")
            
            # Check database size
            if health_status['stats']['database_size_mb'] > 1000:  # 1GB
                health_status['warnings'].append("Database size is large (>1GB)")
            
            # Check inactive chunks ratio
            total = health_status['stats']['total_chunks']
            inactive = health_status['stats']['inactive_chunks']
            
            if total > 0 and (inactive / total) > 0.3:  # >30% inactive
                health_status['warnings'].append("High ratio of inactive chunks (>30%)")
            
            if health_status['issues']:
                health_status['status'] = 'degraded'
            elif health_status['warnings']:
                health_status['status'] = 'warning'
                
        except Exception as e:
            health_status['status'] = 'error'
            health_status['issues'].append(f"Database connectivity error: {str(e)}")
        
        return health_status

# Create global extended database manager
extended_db = ExtendedDatabaseManager()
extended_db = ExtendedDatabaseManager()