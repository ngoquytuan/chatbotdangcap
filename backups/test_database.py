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

# Add project root to path
sys.path.append('.')

from rag_system.api_service.utils.database import ExtendedDatabaseManager, ChunkFilter

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_test_embedding():
    """Create a random test embedding vector"""
    return np.random.randn(384).tolist()

def generate_test_data():
    """Generate realistic test data for chunks"""
    
    test_documents = [
        {
            'document_id': 'lythaito',
            'title': 'Lý Thái Tổ - Vua đầu tiên nhà Lý',
            'category': 'Lịch sử',
            'chunks': [
                {
                    'chunk_id': 'lythaito-000',
                    'text': 'Lý Thái Tổ trị vì từ năm 1009 đến khi qua đời vào năm 1028.',
                    'tokens': 368,
                    'heading': 'Thời kỳ cai trị',
                    'section_index': 0
                },
                {
                    'chunk_id': 'lythaito-001', 
                    'text': 'Thời gian trị vì của ông chủ yếu tập trung vào việc xây dựng đất nước.',
                    'tokens': 326,
                    'heading': 'Thời kỳ cai trị',
                    'section_index': 0
                }
            ]
        },
        {
            'document_id': 'tranquocvuong',
            'title': 'Trần Quốc Vương - Vị vua anh hùng',
            'category': 'Lịch sử',
            'chunks': [
                {
                    'chunk_id': 'tranquocvuong-000',
                    'text': 'Trần Quốc Vương nổi tiếng với chiến thắng trước quân Mông Cổ.',
                    'tokens': 298,
                    'heading': 'Chiến thắng lịch sử',
                    'section_index': 0
                }
            ]
        }
    ]
    
    return test_documents

def test_database_initialization():
    """Test 1: Database initialization"""
    logger.info("=== Test 1: Database Initialization ===")
    
    try:
        # Use a test database
        db = ExtendedDatabaseManager("test_metadata.db")
        
        # Check if tables exist
        with db.get_cursor() as cursor:
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN ('chunks', 'documents', 'audit_log')
            """)
            tables = [row[0] for row in cursor.fetchall()]
        
        required_tables = ['chunks', 'documents', 'audit_log', 'search_analytics']
        missing_tables = set(required_tables) - set(tables)
        
        if missing_tables:
            logger.error(f"Missing tables: {missing_tables}")
            return False
        
        logger.info("✅ All required tables exist")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return False

def test_chunk_insertion():
    """Test 2: Chunk insertion and retrieval"""
    logger.info("=== Test 2: Chunk Insertion ===")
    
    try:
        db = ExtendedDatabaseManager("test_metadata.db")
        test_data = generate_test_data()
        
        inserted_ids = []
        
        for doc in test_data:
            for chunk in doc['chunks']:
                chunk_data = {
                    'chunk_id': chunk['chunk_id'],
                    'document_id': doc['document_id'],
                    'title': doc['title'],
                    'source': f"test_docs/{doc['document_id']}.txt",
                    'text': chunk['text'],
                    'tokens': chunk['tokens'],
                    'heading': chunk['heading'],
                    'section_index': chunk['section_index'],
                    'category': doc['category'],
                    'access_roles': ['all'],
                    'embedding': create_test_embedding()
                }
                
                chunk_id = db.insert_chunk(chunk_data)
                inserted_ids.append(chunk_id)
                logger.info(f"✅ Inserted chunk {chunk['chunk_id']} with ID {chunk_id}")
        
        # Test retrieval
        active_chunks = db.get_active_chunks()
        logger.info(f"✅ Retrieved {len(active_chunks)} active chunks")
        
        # Test retrieval by IDs
        chunks_by_id = db.get_chunks_by_ids(inserted_ids)
        logger.info(f"✅ Retrieved {len(chunks_by_id)} chunks by ID")
        
        return len(inserted_ids) == len(test_data[0]['chunks']) + len(test_data[1]['chunks'])
        
    except Exception as e:
        logger.error(f"❌ Chunk insertion test failed: {e}")
        return False

def test_advanced_filtering():
    """Test 3: Advanced filtering capabilities"""
    logger.info("=== Test 3: Advanced Filtering ===")
    
    try:
        db = ExtendedDatabaseManager("test_metadata.db")
        
        # Test text search
        results = db.query_builder.search_chunks_advanced(
            text_search="Lý Thái Tổ",
            limit=10
        )
        logger.info(f"✅ Text search returned {len(results)} results")
        
        # Test category filtering
        results = db.query_builder.search_chunks_advanced(
            categories=["Lịch sử"],
            limit=10
        )
        logger.info(f"✅ Category filter returned {len(results)} results")
        
        # Test access role filtering
        results = db.query_builder.search_chunks_advanced(
            user_roles=["admin"],
            limit=10
        )
        logger.info(f"✅ Role filter returned {len(results)} results")
        
        # Test date range
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        results = db.query_builder.search_chunks_advanced(
            date_from=yesterday,
            limit=10
        )
        logger.info(f"✅ Date filter returned {len(results)} results")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Advanced filtering test failed: {e}")
        return False

def test_soft_delete():
    """Test 4: Soft delete functionality"""
    logger.info("=== Test 4: Soft Delete ===")
    
    try:
        db = ExtendedDatabaseManager("test_metadata.db")
        
        # Get a chunk to delete
        active_chunks = db.get_active_chunks()
        if not active_chunks:
            logger.error("No active chunks to test soft delete")
            return False
        
        chunk_to_delete = active_chunks[0]['chunk_id']
        
        # Soft delete
        success = db.soft_delete_chunk(
            chunk_id=chunk_to_delete,
            invalidated_by="test_deletion",
            reason="Testing soft delete functionality",
            user_id="test_user"
        )
        
        if not success:
            logger.error("Soft delete operation failed")
            return False
        
        # Verify chunk is no longer active
        active_chunks_after = db.get_active_chunks()
        deleted_chunk_found = any(
            chunk['chunk_id'] == chunk_to_delete 
            for chunk in active_chunks_after
        )
        
        if deleted_chunk_found:
            logger.error("Chunk still appears in active results after soft delete")
            return False
        
        logger.info(f"✅ Successfully soft deleted chunk {chunk_to_delete}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Soft delete test failed: {e}")
        return False

def test_statistics_and_health():
    """Test 5: Statistics and health check"""
    logger.info("=== Test 5: Statistics and Health ===")
    
    try:
        db = ExtendedDatabaseManager("test_metadata.db")
        
        # Test basic statistics
        stats = db.get_database_stats()
        required_stats = ['total_chunks', 'active_chunks', 'inactive_chunks', 'database_size_mb']
        
        for stat in required_stats:
            if stat not in stats:
                logger.error(f"Missing statistic: {stat}")
                return False
        
        logger.info(f"✅ Database stats: {json.dumps(stats, indent=2)}")
        
        # Test detailed chunk statistics
        chunk_stats = db.query_builder.get_chunk_statistics()
        logger.info(f"✅ Chunk statistics: {json.dumps(chunk_stats, indent=2)}")
        
        # Test health check
        health = db.health_check()
        logger.info(f"✅ Health check: {health['status']}")
        
        if health['warnings']:
            logger.info(f"Warnings: {health['warnings']}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Statistics test failed: {e}")
        return False

def test_backup_restore():
    """Test 6: Backup and restore"""
    logger.info("=== Test 6: Backup and Restore ===")
    
    try:
        db = ExtendedDatabaseManager("test_metadata.db")
        
        # Create backup
        backup_path = db.backup_database("test_backup.db")
        logger.info(f"✅ Created backup: {backup_path}")
        
        # Verify backup file exists
        if not Path(backup_path).exists():
            logger.error("Backup file was not created")
            return False
        
        # Test backup size
        backup_size = Path(backup_path).stat().st_size
        original_size = Path("test_metadata.db").stat().st_size
        
        if backup_size == 0:
            logger.error("Backup file is empty")
            return False
        
        logger.info(f"✅ Backup size: {backup_size} bytes (original: {original_size} bytes)")
        
        # Cleanup test backup
        Path(backup_path).unlink()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Backup test failed: {e}")
        return False

def cleanup_test_files():
    """Clean up test files"""
    test_files = ["test_metadata.db", "test_metadata.db-wal", "test_metadata.db-shm"]
    
    for file in test_files:
        file_path = Path(file)
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Cleaned up: {file}")

def main():
    """Run all database tests"""
    logger.info("🚀 Starting Database Layer Tests")
    
    tests = [
        test_database_initialization,
        test_chunk_insertion, 
        test_advanced_filtering,
        test_soft_delete,
        test_statistics_and_health,
        test_backup_restore
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
                logger.info(f"✅ {test.__name__} PASSED")
            else:
                failed += 1
                logger.error(f"❌ {test.__name__} FAILED")
        except Exception as e:
            failed += 1
            logger.error(f"❌ {test.__name__} ERROR: {e}")
    
    logger.info(f"\n=== TEST SUMMARY ===")
    logger.info(f"✅ Passed: {passed}")
    logger.info(f"❌ Failed: {failed}")
    logger.info(f"Total: {passed + failed}")
    
    if failed == 0:
        logger.info("🎉 All tests passed!")
    else:
        logger.error(f"💥 {failed} test(s) failed")
    
    # Cleanup
    cleanup_test_files()

if __name__ == "__main__":
    main()