""" © Daniel P Raven 2024 All Rights Reserved """
"""
Quick test to check database table existence and create missing tables
"""
import os
from qtr_pairing_process.db_management.db_manager import DbManager

def check_and_fix_database():
    """Check if the database has all required tables and create missing ones"""
    print("Checking database structure...")
    
    # Get the current database path from the existing database manager
    try:
        # Create a temporary instance to check the current database
        db_manager = DbManager()
        print(f"Database path: {db_manager.path}/{db_manager.name}")
        
        # Check if matchup_comments table exists
        try:
            tables = db_manager.query_sql("SELECT name FROM sqlite_master WHERE type='table';")
            table_names = [table[0] for table in tables]
            print(f"Existing tables: {table_names}")
            
            if 'matchup_comments' not in table_names:
                print("❌ matchup_comments table is missing!")
                print("Creating matchup_comments table...")
                
                # Read and execute the matchup_comments SQL file
                sql_file_path = 'qtr_pairing_process/db_management/sql/matchup_comments.sql'
                if os.path.exists(sql_file_path):
                    with open(sql_file_path, 'r') as f:
                        sql_content = f.read()
                    
                    # Split and execute each statement
                    statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
                    for statement in statements:
                        if statement:
                            print(f"Executing: {statement[:50]}...")
                            db_manager.execute_sql(statement)
                    
                    print("✅ matchup_comments table created successfully!")
                else:
                    print(f"❌ SQL file not found: {sql_file_path}")
            else:
                print("✅ matchup_comments table exists!")
            
            # Verify the table was created by checking again
            tables = db_manager.query_sql("SELECT name FROM sqlite_master WHERE type='table';")
            table_names = [table[0] for table in tables]
            print(f"Final tables: {table_names}")
            
            # Test a simple comment operation
            if 'matchup_comments' in table_names:
                print("Testing comment functionality...")
                try:
                    # Try to insert a test comment
                    db_manager.upsert_comment_by_name(
                        'default_team_1', 'default_team_2', '0 - Neutral',
                        'default_player_1_1', 'default_player_2_1', 
                        'Test comment - delete this'
                    )
                    print("✅ Comment insertion test passed!")
                    
                    # Try to query it back
                    comment = db_manager.query_comment_by_name(
                        'default_team_1', 'default_team_2', '0 - Neutral',
                        'default_player_1_1', 'default_player_2_1'
                    )
                    if comment:
                        print(f"✅ Comment query test passed! Found: {comment}")
                    
                    # Clean up test comment
                    db_manager.delete_comment_by_name(
                        'default_team_1', 'default_team_2', '0 - Neutral',
                        'default_player_1_1', 'default_player_2_1'
                    )
                    print("✅ Comment deletion test passed!")
                    
                except Exception as e:
                    print(f"❌ Comment functionality test failed: {e}")
            
        except Exception as e:
            print(f"❌ Database check failed: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Database manager initialization failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = check_and_fix_database()
    print(f"\nDatabase check completed: {'✅ SUCCESS' if success else '❌ FAILED'}")