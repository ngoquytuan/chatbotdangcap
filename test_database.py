#!/usr/bin/env python3 test_database.py
#!/usr/bin/env python3
"""
Comprehensive test script for database layer
Tests all database functionality with realistic data
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
import numpy as np
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rag_system.api_service.utils.database import ExtendedDatabaseManager

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

EMBEDDING_DIM = 1024 

def create_test_embedding():
    """Create a random test embedding vector"""
    return np.random.randn(EMBEDDING_DIM).tolist()

def generate_test_data():
    """Generate realistic test data for chunks"""
    return [
        {'document_id': 'lythaito', 'title': 'Lý Thái Tổ - Vua đầu tiên nhà Lý', 'category': 'Lịch sử',
         'chunks': [
             {'chunk_id': 'lythaito-000', 'text': 'Lý Thái Tổ trị vì từ năm 1009 đến khi qua đời vào năm 1028.', 'tokens': 368, 'heading': 'Thời kỳ cai trị', 'section_index': 0},
             {'chunk_id': 'lythaito-001', 'text': 'Thời gian trị vì của ông chủ yếu tập trung vào việc xây dựng đất nước.', 'tokens': 326, 'heading': 'Thời kỳ cai trị', 'section_index': 0}
         ]},
        {'document_id': 'tranquocvuong', 'title': 'Trần Quốc Vương - Vị vua anh hùng', 'category': 'Lịch sử',
         'chunks': [
             {'chunk_id': 'tranquocvuong-000', 'text': 'Trần Quốc Vương nổi tiếng với chiến thắng trước quân Mông Cổ.', 'tokens': 298, 'heading': 'Chiến thắng lịch sử', 'section_index': 0}
         ]}
    ]

def test_database_initialization():
    logger.info("=== Test 1: Database Initialization ===")
    try:
        db = ExtendedDatabaseManager("test_metadata.db")
        with db.get_cursor() as cursor:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
        required_tables = ['chunks', 'documents', 'audit_log', 'search_analytics']
        missing_tables = set(required_tables) - set(tables)
        if missing_tables:
            logger.error(f"Missing tables: {missing_tables}")
            return False
        logger.info("✅ All required tables exist")
        return True
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}", exc_info=True)
        return False

def test_chunk_insertion():
    logger.info("=== Test 2: Chunk Insertion ===")
    try:
        db = ExtendedDatabaseManager("test_metadata.db")
        test_data = generate_test_data()
        inserted_ids = []
        for doc in test_data:
            for chunk in doc['chunks']:
                chunk_data = {
                    'chunk_id': chunk['chunk_id'], 'document_id': doc['document_id'],
                    'title': doc['title'], 'source': f"test_docs/{doc['document_id']}.txt",
                    'version': '1.0', 'language': 'vi', 'text': chunk['text'],
                    'tokens': chunk['tokens'], 'heading': chunk['heading'], 'heading_level': 1,
                    'section_index': chunk.get('section_index', 0), 'section_chunk_index': 0,
                    'start_page': 1, 'end_page': 1, 'access_roles': ['all'],
                    'confidentiality_level': 'internal', 'author': 'Test Author',
                    'category': doc.get('category', 'Uncategorized'), 'keywords': ['test'],
                    'summary': f"Summary for {chunk['chunk_id']}", 'metadata': {'test_key': 'test_value'},
                    'embedding': create_test_embedding()
                }
                chunk_id = db.insert_chunk(chunk_data)
                inserted_ids.append(chunk_id)
        logger.info(f"✅ Inserted {len(inserted_ids)} chunks")
        active_chunks = db.get_active_chunks()
        logger.info(f"✅ Retrieved {len(active_chunks)} active chunks")
        chunks_by_id = db.get_chunks_by_ids(inserted_ids)
        logger.info(f"✅ Retrieved {len(chunks_by_id)} chunks by ID")
        return len(inserted_ids) == 3
    except Exception as e:
        logger.error(f"❌ Chunk insertion test failed: {e}", exc_info=True)
        return False

def test_advanced_filtering():
    logger.info("=== Test 3: Advanced Filtering ===")
    try:
        db = ExtendedDatabaseManager("test_metadata.db")
        # Test 1: Text search
        results = db.query_builder.search_chunks_advanced(text_search="Lý Thái Tổ", limit=10)
        logger.info(f"✅ Text search returned {len(results)} results")
        assert len(results) == 2, "Text search should find 2 'Lý Thái Tổ' chunks"

        # Test 2: Category search
        results = db.query_builder.search_chunks_advanced(categories=["Lịch sử"], limit=10)
        logger.info(f"✅ Category filter returned {len(results)} results")
        assert len(results) == 3, "Category search should find all 3 history chunks"

        # FIX: Sửa lại logic kiểm thử cho access role
        # Một user có vai trò 'admin' VẪN NÊN thấy các chunk dành cho 'all'.
        results = db.query_builder.search_chunks_advanced(user_roles=["admin"], limit=10)
        logger.info(f"✅ Role filter (admin) returned {len(results)} results for 'all' chunks")
        assert len(results) == 3, "A user with 'admin' role should see chunks marked for 'all'"

        return True
    except Exception as e:
        logger.error(f"❌ Advanced filtering test failed: {e}", exc_info=True)
        return False

def test_soft_delete():
    logger.info("=== Test 4: Soft Delete ===")
    try:
        db = ExtendedDatabaseManager("test_metadata.db")
        active_chunks_before = db.get_active_chunks()
        if not active_chunks_before:
            logger.error("No active chunks to test soft delete"); return False
        
        chunk_to_delete = active_chunks_before[0]['chunk_id']
        success = db.soft_delete_chunk(chunk_id=chunk_to_delete)
        if not success:
            logger.error("Soft delete operation failed"); return False
        
        active_chunks_after = db.get_active_chunks()
        assert len(active_chunks_after) == len(active_chunks_before) - 1
        
        logger.info(f"✅ Successfully soft deleted chunk {chunk_to_delete}")
        return True
    except Exception as e:
        logger.error(f"❌ Soft delete test failed: {e}", exc_info=True)
        return False

def test_statistics_and_health():
    logger.info("=== Test 5: Statistics and Health ===")
    try:
        db = ExtendedDatabaseManager("test_metadata.db")
        stats = db.get_database_stats()
        logger.info(f"✅ Database stats retrieved: {stats['total_chunks']} total chunks")
        assert 'total_chunks' in stats

        health = db.health_check()
        logger.info(f"✅ Health check status: {health['status']}")
        assert health['status'] != 'error'
        return True
    except Exception as e:
        logger.error(f"❌ Statistics test failed: {e}", exc_info=True)
        return False

def test_backup_restore():
    logger.info("=== Test 6: Backup and Restore ===")
    backup_file = Path("test_backup.db")
    try:
        db = ExtendedDatabaseManager("test_metadata.db")
        backup_path = db.backup_database(str(backup_file))
        assert backup_file.exists() and backup_file.stat().st_size > 0
        logger.info(f"✅ Backup created successfully at {backup_path}")
        return True
    except Exception as e:
        logger.error(f"❌ Backup test failed: {e}", exc_info=True)
        return False
    finally:
        if backup_file.exists(): backup_file.unlink()

def cleanup_test_files():
    """Clean up test files, ensuring connections are closed first."""
    logger.info("--- Cleaning up test files ---")
    # FIX: Tạo một instance để gọi hàm đóng kết nối
    db_to_close = ExtendedDatabaseManager("test_metadata.db")
    db_to_close.close_connections()
    
    test_files = ["test_metadata.db", "test_metadata.db-wal", "test_metadata.db-shm", "test_backup.db"]
    for file in test_files:
        file_path = Path(file)
        if file_path.exists():
            try:
                file_path.unlink()
                logger.info(f"Cleaned up: {file}")
            except OSError as e:
                logger.warning(f"Could not clean up {file}: {e}")

def main():
    logger.info("🚀 Starting Database Layer Tests")
    cleanup_test_files()

    tests = [
        test_database_initialization, test_chunk_insertion, 
        test_advanced_filtering, test_soft_delete,
        test_statistics_and_health, test_backup_restore
    ]
    passed, failed = 0, 0
    
    for test_func in tests:
        if test_func():
            passed += 1
        else:
            failed += 1
            logger.error(f"Stopping tests due to failure in: {test_func.__name__}")
            break
    
    logger.info("\n=== TEST SUMMARY ===")
    logger.info(f"✅ Passed: {passed}")
    logger.info(f"❌ Failed: {failed}")
    
    if failed == 0: logger.info("🎉 All tests passed!")
    else: logger.error(f"💥 {failed} test(s) failed")
    
    cleanup_test_files()

if __name__ == "__main__":
    main()