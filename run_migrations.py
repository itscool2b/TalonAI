#!/usr/bin/env python
import os
import sys
import django
from django.conf import settings
from django.core.management import execute_from_command_line

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TalonAILinux.settings')
    django.setup()
    
    # Run migrations
    execute_from_command_line(['manage.py', 'migrate']) 