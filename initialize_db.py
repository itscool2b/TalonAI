#!/usr/bin/env python
"""
Database initialization script for TalonAI
This script ensures all migrations are applied properly
"""
import os
import sys
import django
from django.core.management import execute_from_command_line

def main():
    """Run database initialization"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TalonAILinux.settings')
    django.setup()
    
    print("🔄 Running database migrations...")
    try:
        execute_from_command_line(['manage.py', 'migrate'])
        print("✅ Database migrations completed successfully!")
    except Exception as e:
        print(f"❌ Error running migrations: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 