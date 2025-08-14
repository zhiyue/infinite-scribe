#!/bin/bash

# Local Docker build script for Infinite Scribe API Gateway
# Usage: ./scripts/docker/build.sh [OPTIONS]

set -e -u -o pipefail

# Default values
IMAGE_NAME="infinite-scribe"
TAG="local"
PLATFORM="linux/amd64"
SERVICE_TYPE="api-gateway"
PUSH=false
REGISTRY="ghcr.io"
FULL_IMAGE_NAME=""
NO_CACHE=false
CACHE_DIR="${HOME}/.cache/buildx"
TEST=false
VERBOSE="${VERBOSE:-false}"

# Enable Docker Buildkit
export DOCKER_BUILDKIT=1

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show help
show_help() {
    cat << EOF
Usage: $0 [OPTIONS]

Options:
  -h, --help              Show this help message
  -n, --name NAME         Docker image name (default: infinite-scribe)
  -t, --tag TAG           Docker image tag (default: local)
  -p, --platform PLATFORM Multi-platform build (default: linux/amd64)
  -s, --service SERVICE   Service type to test (default: api-gateway)
  -r, --registry REGISTRY Registry prefix (default: ghcr.io)
  --push                  Push to registry
  --no-cache              Build without cache
  --test                  Run container after build for testing
  --multi-arch            Build for multiple architectures (linux/amd64,linux/arm64)
  --cache-dir DIR         Cache directory (default: ~/.cache/buildx)
  --verbose               Enable verbose build output (--progress=plain)

Examples:
  $0                      Build local image
  $0 -n myapp -t v1.0.0   Build with custom name and tag
  $0 --multi-arch         Build for multiple architectures
  $0 --test               Build and run container for testing
  $0 --push -t latest     Build and push to registry
  $0 --cache-dir ./cache  Use custom cache directory

EOF
}

# Function to check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    # Check Docker Buildx
    if ! docker buildx version &> /dev/null; then
        print_error "Docker Buildx is not available"
        exit 1
    fi
    
    # Check if we're in the right directory
    if [ ! -f "apps/backend/Dockerfile" ]; then
        print_error "Dockerfile not found. Are you in the project root?"
        exit 1
    fi
    
    # Set up QEMU for multi-platform builds if needed
    if [[ "$PLATFORM" == *"arm64"* ]] || [[ "$PLATFORM" == *","* ]]; then
        print_info "Multi-platform build detected, setting up QEMU..."
        if ! docker run --privileged --rm tonistiigi/binfmt --install all >/dev/null 2>&1; then
            print_warning "Failed to set up QEMU for multi-platform builds"
            print_info "Multi-platform build may still work if QEMU is already configured"
        fi
    fi
    
    print_success "Prerequisites check passed"
}

# Function to build image
build_image() {
    print_info "Building Docker image..."
    
    # Set up full image name
    if [ "$PUSH" = true ]; then
        FULL_IMAGE_NAME="$REGISTRY/$IMAGE_NAME:$TAG"
    else
        FULL_IMAGE_NAME="$IMAGE_NAME:$TAG"
    fi
    
    # Create cache directory if it doesn't exist
    mkdir -p "$CACHE_DIR"
    
    # Build command array for safer execution
    local build_cmd=(
        "docker" "buildx" "build"
        "--platform" "$PLATFORM"
        "-f" "apps/backend/Dockerfile"
        "-t" "$FULL_IMAGE_NAME"
    )
    
    # Set build progress output based on VERBOSE setting
    if [ "$VERBOSE" = true ]; then
        build_cmd+=("--progress" "plain")
    else
        build_cmd+=("--progress" "auto")
    fi
    
    # Set up cache arguments
    if [ "$NO_CACHE" != true ]; then
        build_cmd+=(
            "--cache-from" "type=local,src=$CACHE_DIR"
            "--cache-to" "type=local,dest=$CACHE_DIR"
        )
    else
        # Truly disable all caching, including Docker layer cache
        build_cmd+=("--no-cache")
    fi
    
    if [ "$PUSH" = true ]; then
        build_cmd+=("--push")
    else
        build_cmd+=("--load")
    fi
    
    build_cmd+=(".")
    
    print_info "Running: ${build_cmd[*]}"
    
    # Execute build
    if "${build_cmd[@]}"; then
        print_success "Docker image built successfully: $FULL_IMAGE_NAME"
    else
        print_error "Docker build failed"
        exit 1
    fi
}

# Function to get image size
get_image_size() {
    if [ "$PUSH" != true ]; then
        local size=$(docker images --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}" --no-trunc | grep "$FULL_IMAGE_NAME" | awk '{print $2}')
        if [ -n "$size" ]; then
            print_info "Image size: $size"
        fi
    fi
}

# Function to test container
test_container() {
    print_info "Testing container..."
    
    local container_name="infinite-scribe-test-$$"
    
    # Set up automatic cleanup
    cleanup_container() {
        if [ -n "${container_name:-}" ]; then
            docker stop "$container_name" >/dev/null 2>&1 || true
            docker rm "$container_name" >/dev/null 2>&1 || true
        fi
    }
    trap cleanup_container EXIT
    
    # Run container
    print_info "Starting container: $container_name"
    if ! docker run -d \
        --name "$container_name" \
        -p 8000:8000 \
        -e SERVICE_TYPE="$SERVICE_TYPE" \
        "$FULL_IMAGE_NAME"; then
        print_error "Failed to start container"
        exit 1
    fi
    
    # Wait for container to start
    sleep 5
    
    # Check if container is running
    if docker ps --filter "name=$container_name" --format "{{.Names}}" | grep -q "$container_name"; then
        print_success "Container started successfully"
        
        # Test health endpoint for API Gateway
        if [ "$SERVICE_TYPE" = "api-gateway" ]; then
            print_info "Testing health endpoint..."
            if curl -f http://localhost:8000/health > /dev/null 2>&1; then
                print_success "Health check passed"
            else
                print_warning "Health check failed or endpoint not available"
                # Show container logs for debugging
                print_info "Container logs for debugging:"
                docker logs "$container_name"
            fi
        fi
        
        # Show container logs
        print_info "Container logs:"
        docker logs "$container_name"
        
    else
        print_error "Container failed to start"
        docker logs "$container_name"
        exit 1
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -n|--name)
            IMAGE_NAME="$2"
            shift 2
            ;;
        -t|--tag)
            TAG="$2"
            shift 2
            ;;
        -p|--platform)
            PLATFORM="$2"
            shift 2
            ;;
        -s|--service)
            SERVICE_TYPE="$2"
            shift 2
            ;;
        -r|--registry)
            REGISTRY="$2"
            shift 2
            ;;
        --cache-dir)
            CACHE_DIR="$2"
            shift 2
            ;;
        --push)
            PUSH=true
            shift
            ;;
        --no-cache)
            NO_CACHE=true
            shift
            ;;
        --test)
            TEST=true
            shift
            ;;
        --multi-arch)
            PLATFORM="linux/amd64,linux/arm64"
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Main execution
print_info "Starting Docker build process..."
print_info "Image: $IMAGE_NAME"
print_info "Tag: $TAG"
print_info "Platform: $PLATFORM"
print_info "Service: $SERVICE_TYPE"
print_info "Push: $PUSH"

# Check prerequisites
check_prerequisites

# Build image
build_image

# Get image size
get_image_size

# Test container if requested
if [ "$TEST" = true ]; then
    test_container
fi

print_success "Build process completed successfully!"