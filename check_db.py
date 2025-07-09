#!/usr/bin/env python
"""
Simple database connection check for TalonAI
"""
import os
import sys
import django
from django.db import connection
from django.core.management import execute_from_command_line

def check_database():
    """Check if database is accessible"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TalonAILinux.settings')
    django.setup()
    
    try:
        # Try to get a database cursor
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            if result:
                print("✅ Database connection successful!")
                return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

if __name__ == '__main__':
    success = check_database()
    sys.exit(0 if success else 1) 