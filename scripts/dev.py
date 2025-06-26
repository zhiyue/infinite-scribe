#!/usr/bin/env python
"""开发辅助脚本 - 简化开发工作流"""
import subprocess
import sys
import os
from pathlib import Path

# 服务配置
SERVICES = {
    "api-gateway": {
        "module": "apps.api-gateway.app.main",
        "command": "uvicorn {module}:app --reload --port 8000"
    },
    "worldsmith-agent": {
        "module": "apps.worldsmith-agent.agent.main",
        "command": "python -m {module}"
    },
    "plotmaster-agent": {
        "module": "apps.plotmaster-agent.agent.main", 
        "command": "python -m {module}"
    },
    "outliner-agent": {
        "module": "apps.outliner-agent.agent.main",
        "command": "python -m {module}"
    },
    "director-agent": {
        "module": "apps.director-agent.agent.main",
        "command": "python -m {module}"
    },
    "characterexpert-agent": {
        "module": "apps.characterexpert-agent.agent.main",
        "command": "python -m {module}"
    },
    "worldbuilder-agent": {
        "module": "apps.worldbuilder-agent.agent.main",
        "command": "python -m {module}"
    },
    "writer-agent": {
        "module": "apps.writer-agent.agent.main",
        "command": "python -m {module}"
    },
    "critic-agent": {
        "module": "apps.critic-agent.agent.main",
        "command": "python -m {module}"
    },
    "factchecker-agent": {
        "module": "apps.factchecker-agent.agent.main",
        "command": "python -m {module}"
    },
    "rewriter-agent": {
        "module": "apps.rewriter-agent.agent.main",
        "command": "python -m {module}"
    },
}

def run_service(service_name):
    """运行指定服务"""
    if service_name not in SERVICES:
        print(f"❌ Unknown service: {service_name}")
        print(f"Available services: {', '.join(SERVICES.keys())}")
        sys.exit(1)
    
    service = SERVICES[service_name]
    command = service["command"].format(module=service["module"])
    
    print(f"🚀 Running {service_name}...")
    print(f"Command: {command}")
    
    try:
        subprocess.run(command, shell=True, check=True)
    except KeyboardInterrupt:
        print(f"\n⏹️  Stopped {service_name}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running {service_name}: {e}")
        sys.exit(1)

def test(service_name=None, coverage=False):
    """运行测试"""
    if service_name:
        test_path = f"apps/{service_name}/tests"
        if not Path(test_path).exists():
            print(f"⚠️  No tests found for {service_name}")
            return
        cmd = f"pytest {test_path} -v"
    else:
        cmd = "pytest -v"
    
    if coverage:
        cmd += " --cov --cov-report=html --cov-report=term"
    
    print(f"🧪 Running tests...")
    subprocess.run(cmd, shell=True)

def lint():
    """运行代码检查"""
    print("🔍 Running code checks...")
    
    commands = [
        ("Ruff check", "ruff check ."),
        ("Black check", "black --check ."),
        ("MyPy", "mypy apps/"),
    ]
    
    failed = False
    for name, cmd in commands:
        print(f"\n📋 {name}...")
        result = subprocess.run(cmd, shell=True)
        if result.returncode != 0:
            failed = True
    
    if failed:
        print("\n❌ Some checks failed!")
        sys.exit(1)
    else:
        print("\n✅ All checks passed!")

def format_code():
    """格式化代码"""
    print("🎨 Formatting code...")
    
    commands = [
        ("Ruff fix", "ruff check --fix ."),
        ("Black", "black ."),
    ]
    
    for name, cmd in commands:
        print(f"\n📋 {name}...")
        subprocess.run(cmd, shell=True)
    
    print("\n✅ Code formatting complete!")

def install():
    """安装/更新依赖"""
    print("📦 Installing dependencies...")
    subprocess.run("uv sync --dev", shell=True, check=True)
    print("✅ Dependencies installed!")

def clean():
    """清理临时文件"""
    print("🧹 Cleaning up...")
    
    patterns = [
        "**/__pycache__",
        "**/*.pyc",
        "**/.pytest_cache",
        "**/.coverage",
        "**/htmlcov",
        "**/.mypy_cache",
        "**/.ruff_cache",
    ]
    
    for pattern in patterns:
        for path in Path(".").glob(pattern):
            if path.is_dir():
                import shutil
                shutil.rmtree(path)
            else:
                path.unlink()
    
    print("✅ Cleanup complete!")

def docker_build(service_name=None):
    """构建Docker镜像"""
    if service_name:
        if service_name not in SERVICES:
            print(f"❌ Unknown service: {service_name}")
            sys.exit(1)
        
        dockerfile_path = f"apps/{service_name}/Dockerfile"
        if not Path(dockerfile_path).exists():
            print(f"❌ No Dockerfile found for {service_name}")
            sys.exit(1)
        
        print(f"🐳 Building Docker image for {service_name}...")
        cmd = f"docker build -t infinite-scribe/{service_name}:latest -f {dockerfile_path} ."
        subprocess.run(cmd, shell=True, check=True)
    else:
        print("🐳 Building all Docker images...")
        subprocess.run("docker-compose build", shell=True, check=True)
    
    print("✅ Docker build complete!")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Infinite Scribe 开发辅助工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/dev.py run api-gateway        # 运行API网关
  python scripts/dev.py test                   # 运行所有测试
  python scripts/dev.py test api-gateway       # 运行特定服务的测试
  python scripts/dev.py lint                   # 检查代码风格
  python scripts/dev.py format                 # 格式化代码
  python scripts/dev.py install                # 安装依赖
  python scripts/dev.py docker-build           # 构建所有Docker镜像
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # run 命令
    run_parser = subparsers.add_parser("run", help="运行服务")
    run_parser.add_argument("service", choices=SERVICES.keys(), help="服务名称")
    
    # test 命令
    test_parser = subparsers.add_parser("test", help="运行测试")
    test_parser.add_argument("service", nargs="?", help="服务名称（可选）")
    test_parser.add_argument("--coverage", "-c", action="store_true", help="生成覆盖率报告")
    
    # lint 命令
    subparsers.add_parser("lint", help="运行代码检查")
    
    # format 命令
    subparsers.add_parser("format", help="格式化代码")
    
    # install 命令
    subparsers.add_parser("install", help="安装/更新依赖")
    
    # clean 命令
    subparsers.add_parser("clean", help="清理临时文件")
    
    # docker-build 命令
    docker_parser = subparsers.add_parser("docker-build", help="构建Docker镜像")
    docker_parser.add_argument("service", nargs="?", help="服务名称（可选）")
    
    args = parser.parse_args()
    
    # 确保在项目根目录运行
    if not Path("pyproject.toml").exists():
        print("❌ 请在项目根目录运行此脚本")
        sys.exit(1)
    
    # 执行命令
    if args.command == "run":
        run_service(args.service)
    elif args.command == "test":
        test(args.service, args.coverage)
    elif args.command == "lint":
        lint()
    elif args.command == "format":
        format_code()
    elif args.command == "install":
        install()
    elif args.command == "clean":
        clean()
    elif args.command == "docker-build":
        docker_build(args.service)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()