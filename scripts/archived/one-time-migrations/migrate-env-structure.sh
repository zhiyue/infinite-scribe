#!/bin/bash
# Migrate from single .env to layered environment structure

set -e

echo "🔄 Migrating to layered environment structure..."

# Backup existing .env if it exists and is not a symlink
if [ -f .env ] && [ ! -L .env ]; then
    echo "📦 Backing up existing .env to .env.all-in-one.backup"
    cp .env .env.all-in-one.backup
    
    # Extract infrastructure variables
    echo "🏗️  Creating .env.infrastructure from existing .env"
    grep -E '^(POSTGRES_|REDIS_|NEO4J_|MINIO_|KAFKA_|MILVUS_|DEV_SERVER_)' .env > .env.infrastructure || true
    
    # Add missing infrastructure variables if needed
    if ! grep -q "DEV_SERVER_IP" .env.infrastructure; then
        echo "DEV_SERVER_IP=192.168.2.201" >> .env.infrastructure
    fi
    
    # Remove old .env and create symlink
    rm .env
fi

# Create symlink if it doesn't exist
if [ ! -L .env ]; then
    echo "🔗 Creating symlink: .env -> .env.infrastructure"
    ln -s .env.infrastructure .env
fi

# Create example files if they don't exist
for template in frontend backend agents; do
    if [ ! -f .env.${template}.example ]; then
        echo "⚠️  Missing .env.${template}.example - please run git pull"
    fi
done

echo "✅ Migration complete!"
echo ""
echo "📋 Next steps:"
echo "1. Review .env.infrastructure for infrastructure variables"
echo "2. Create application-specific env files:"
echo "   - cp .env.frontend.example .env.frontend"
echo "   - cp .env.backend.example .env.backend"  
echo "   - cp .env.agents.example .env.agents"
echo "3. Update application env files with values from .env.all-in-one.backup"
echo "4. Deploy with: pnpm infra:up"