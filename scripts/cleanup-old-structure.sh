#!/bin/bash
# Script to clean up old backend structure after migration

echo "This script will remove the old backend structure directories."
echo "Make sure you have migrated all necessary code to apps/backend first!"
echo ""
read -p "Are you sure you want to continue? (y/N) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "Removing old directories..."
    
    # Remove old agent directories
    rm -rf apps/worldsmith-agent
    rm -rf apps/plotmaster-agent
    rm -rf apps/outliner-agent
    rm -rf apps/director-agent
    rm -rf apps/characterexpert-agent
    rm -rf apps/worldbuilder-agent
    rm -rf apps/writer-agent
    rm -rf apps/critic-agent
    rm -rf apps/factchecker-agent
    rm -rf apps/rewriter-agent
    
    # Remove old api-gateway if it exists
    rm -rf apps/api-gateway
    
    echo "Cleanup completed!"
else
    echo "Cleanup cancelled."
fi