#!/bin/bash
# Startup script for TalonAI Backend

echo "🚀 Starting TalonAI Backend..."

# Skip migrations during deployment to avoid database pool issues
echo "⏭️  Skipping database migrations during deployment..."
echo "📝 Run migrations manually if needed: python manage.py migrate"

# Start the server directly
echo "🌟 Starting server..."
exec "$@" 