#!/bin/bash
# Startup script for TalonAI Backend

echo "🚀 Starting TalonAI Backend..."

# Run database migrations
echo "🔄 Running database migrations..."
python manage.py migrate

# Check if migrations were successful
if [ $? -eq 0 ]; then
    echo "✅ Database migrations completed successfully!"
else
    echo "❌ Database migrations failed!"
    exit 1
fi

# Start the server
echo "🌟 Starting server..."
exec "$@" 