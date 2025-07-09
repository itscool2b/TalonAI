#!/bin/bash
# Startup script for TalonAI Backend

echo "🚀 Starting TalonAI Backend..."

# Function to retry database migrations with backoff
retry_migrations() {
    local max_attempts=5
    local wait_time=10
    
    for ((i=1; i<=max_attempts; i++)); do
        echo "🔄 Running database migrations (attempt $i/$max_attempts)..."
        
        if python manage.py migrate --verbosity=1; then
            echo "✅ Database migrations completed successfully!"
            return 0
        else
            if [ $i -eq $max_attempts ]; then
                echo "❌ Database migrations failed after $max_attempts attempts!"
                echo "⚠️  Starting server without migrations - memory features may be limited"
                return 1
            else
                echo "⏳ Migration failed, waiting ${wait_time}s before retry..."
                sleep $wait_time
                wait_time=$((wait_time + 5))  # Increase wait time for next retry
            fi
        fi
    done
}

# Try to run migrations, but don't fail if they don't work
retry_migrations

# Start the server regardless of migration status
echo "🌟 Starting server..."
exec "$@" 