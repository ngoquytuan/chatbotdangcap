#!/usr/bin/env python3
"""
Fixed Environment Checker for FAISS RAG System
Fixes Unicode encoding issues and properly detects GPU environment
"""

import sys
import subprocess
import platform
import json
import logging
import os
from pathlib import Path
import importlib.util

# Fix Unicode encoding for Windows
if platform.system() == "Windows":
    # Set console encoding to UTF-8
    os.environ["PYTHONIOENCODING"] = "utf-8"

# Setup logging with UTF-8 encoding
def setup_logging():
    """Setup logging with proper encoding for Windows"""
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    
    # Create logs directory
    Path('logs').mkdir(exist_ok=True)
    
    handlers = []
    
    # File handler with UTF-8 encoding
    file_handler = logging.FileHandler('logs/environment_check.log', encoding='utf-8')
    file_handler.setFormatter(logging.Formatter(log_format))
    handlers.append(file_handler)
    
    # Console handler with safe output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(log_format))
    handlers.append(console_handler)
    
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=handlers
    )
    
    return logging.getLogger(__name__)

logger = setup_logging()

def safe_log(message, level="INFO"):
    """Safe logging that handles Unicode characters"""
    try:
        if level == "INFO":
            logger.info(message)
        elif level == "ERROR":
            logger.error(message)
        elif level == "WARNING":
            logger.warning(message)
    except UnicodeEncodeError:
        # Fallback to ASCII-safe version
        safe_message = message.encode('ascii', 'replace').decode('ascii')
        if level == "INFO":
            logger.info(f"[OK] {safe_message}")
        elif level == "ERROR":
            logger.error(f"[ERROR] {safe_message}")
        elif level == "WARNING":
            logger.warning(f"[WARN] {safe_message}")

class EnvironmentChecker:
    def __init__(self):
        self.results = {
            'python_version': False,
            'virtual_env': False,
            'cuda_available': False,
            'gpu_detected': False,
            'packages_installed': False,
            'gpu_info': []
        }
    
    def check_python_version(self):
        """Check Python version compatibility"""
        safe_log("Checking Python version...")
        version = sys.version_info
        
        if version.major == 3 and version.minor >= 8:
            safe_log(f"[OK] Python {version.major}.{version.minor}.{version.micro} is compatible")
            self.results['python_version'] = True
            return True
        else:
            safe_log(f"[ERROR] Python {version.major}.{version.minor} not supported. Need Python 3.8+", "ERROR")
            return False
    
    def check_virtual_environment(self):
        """Check if running in virtual environment"""
        safe_log("Checking virtual environment...")
        
        # Check for venv
        if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            safe_log("[OK] Running in virtual environment (venv)")
            self.results['virtual_env'] = True
            return True
        
        # Check for conda
        if 'CONDA_DEFAULT_ENV' in os.environ:
            env_name = os.environ['CONDA_DEFAULT_ENV']
            safe_log(f"[OK] Running in conda environment: {env_name}")
            self.results['virtual_env'] = True
            return True
        
        safe_log("[WARN] Not in virtual environment - recommended to use venv or conda", "WARNING")
        return False
    
    def check_cuda_and_gpu(self):
        """Comprehensive CUDA and GPU check"""
        safe_log("Checking CUDA and GPU availability...")
        
        # Check NVCC
        try:
            result = subprocess.run(['nvcc', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                cuda_info = result.stdout.split('release')[1].split(',')[0].strip()
                safe_log(f"[OK] CUDA toolkit found - version: {cuda_info}")
                self.results['cuda_available'] = True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            safe_log("[WARN] NVCC not found in PATH", "WARNING")
        
        # Check GPU via nvidia-smi
        try:
            result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total', 
                                   '--format=csv,noheader,nounits'], 
                                  capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                gpus = result.stdout.strip().split('\n')
                for i, gpu_line in enumerate(gpus):
                    if gpu_line.strip():
                        name, memory = gpu_line.split(', ')
                        gpu_info = {'id': i, 'name': name.strip(), 'memory_mb': int(memory)}
                        self.results['gpu_info'].append(gpu_info)
                        safe_log(f"[OK] GPU {i}: {name.strip()} ({memory} MB)")
                
                self.results['gpu_detected'] = len(self.results['gpu_info']) > 0
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            safe_log("[WARN] nvidia-smi not found", "WARNING")
        
        # Check PyTorch CUDA
        try:
            import torch
            if torch.cuda.is_available():
                device_count = torch.cuda.device_count()
                safe_log(f"[OK] PyTorch detects {device_count} CUDA devices")
                for i in range(device_count):
                    device_name = torch.cuda.get_device_name(i)
                    safe_log(f"[OK] PyTorch GPU {i}: {device_name}")
                self.results['cuda_available'] = True
                return True
            else:
                safe_log("[WARN] PyTorch CUDA not available", "WARNING")
        except ImportError:
            safe_log("[WARN] PyTorch not installed", "WARNING")
        
        return self.results['cuda_available'] or self.results['gpu_detected']
    
    def check_required_packages(self):
        """Check if required packages are installed"""
        safe_log("Checking required packages...")
        
        required_packages = {
            'torch': 'PyTorch',
            'faiss': 'FAISS',
            'sentence_transformers': 'Sentence Transformers',
            'fastapi': 'FastAPI',
            'uvicorn': 'Uvicorn',
            'numpy': 'NumPy',
            'sqlite3': 'SQLite3 (built-in)'
        }
        
        installed = {}
        missing = []
        
        for package, name in required_packages.items():
            try:
                if package == 'sqlite3':
                    import sqlite3
                    installed[package] = sqlite3.sqlite_version
                elif package == 'faiss':
                    import faiss
                    # Test FAISS functionality
                    test_index = faiss.IndexFlatL2(128)
                    installed[package] = "OK (tested)"
                else:
                    module = importlib.import_module(package)
                    version = getattr(module, '__version__', 'unknown')
                    installed[package] = version
                
                safe_log(f"[OK] {name}: {installed[package]}")
                
            except ImportError:
                missing.append(package)
                safe_log(f"[ERROR] {name} not installed", "ERROR")
        
        if not missing:
            safe_log("[OK] All required packages are installed")
            self.results['packages_installed'] = True
            return True
        else:
            safe_log(f"[ERROR] Missing packages: {', '.join(missing)}", "ERROR")
            return False
    
    def install_missing_packages(self):
        """Install missing packages based on environment"""
        safe_log("Installing missing packages...")
        
        # Determine FAISS version based on CUDA availability
        if self.results['cuda_available']:
            faiss_package = "faiss-gpu"
            safe_log("[INFO] Installing FAISS-GPU for CUDA support")
        else:
            faiss_package = "faiss-cpu"
            safe_log("[INFO] Installing FAISS-CPU")
        
        packages = [
            "fastapi>=0.104.0",
            "uvicorn[standard]>=0.24.0", 
            "sentence-transformers>=2.2.2",
            "numpy>=1.24.0",
            "pydantic>=2.0.0",
            "aiofiles>=23.0.0",
            "python-multipart>=0.0.6",
            "rank-bm25>=0.2.2",
            faiss_package
        ]
        
        # Install PyTorch with CUDA if available
        if self.results['cuda_available']:
            safe_log("[INFO] Installing PyTorch with CUDA 11.8 support")
            try:
                subprocess.run([
                    sys.executable, '-m', 'pip', 'install', 
                    'torch', '--index-url', 'https://download.pytorch.org/whl/cu118'
                ], check=True, timeout=300)
                safe_log("[OK] PyTorch with CUDA installed")
            except subprocess.CalledProcessError:
                safe_log("[ERROR] Failed to install PyTorch with CUDA", "ERROR")
        
        # Install other packages
        success_count = 0
        for package in packages:
            try:
                safe_log(f"Installing {package}...")
                subprocess.run([
                    sys.executable, '-m', 'pip', 'install', package
                ], check=True, timeout=180)
                success_count += 1
                safe_log(f"[OK] {package} installed")
            except subprocess.CalledProcessError:
                safe_log(f"[ERROR] Failed to install {package}", "ERROR")
        
        return success_count == len(packages)
    
    def create_project_structure(self):
        """Create proper project structure"""
        safe_log("Creating project structure...")
        
        structure = {
            'rag_system': {
                'api_service': {
                    'retrieval': ['__init__.py', 'faiss_retriever.py', 'bm25_retriever.py', 'hybrid_retriever.py'],
                    'models': ['__init__.py', 'embeddings.py', 'schema.py'],
                    'utils': ['__init__.py', 'database.py', 'indexing.py'],
                    'config': ['__init__.py', 'settings.py']
                },
                'data': {
                    'raw_documents': [],
                    'ingested_json': [],
                    'indexes': []
                },
                'logs': [],
                'tests': ['__init__.py', 'test_retrieval.py']
            },
            'docker': ['Dockerfile', 'docker-compose.yml'],
            'scripts': ['init_db.py', 'rebuild_index.py']
        }
        
        def create_structure(base_path, structure_dict):
            for name, contents in structure_dict.items():
                path = Path(base_path) / name
                
                if isinstance(contents, dict):
                    path.mkdir(exist_ok=True)
                    safe_log(f"Created directory: {path}")
                    create_structure(path, contents)
                elif isinstance(contents, list):
                    path.mkdir(exist_ok=True)
                    safe_log(f"Created directory: {path}")
                    for file_name in contents:
                        file_path = path / file_name
                        if not file_path.exists():
                            file_path.touch()
                            safe_log(f"Created file: {file_path}")
        
        create_structure('.', structure)
        
        # Create .env template
        env_content = f"""# RAG System Configuration
CUDA_AVAILABLE={'true' if self.results['cuda_available'] else 'false'}
EMBEDDING_DEVICE={'cuda' if self.results['cuda_available'] else 'cpu'}
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
"""
        
        with open('.env', 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        safe_log("[OK] Project structure created")
        safe_log("[OK] .env file created with detected settings")
    
    def generate_report(self):
        """Generate environment report"""
        safe_log("=== ENVIRONMENT REPORT ===")
        safe_log(f"Platform: {platform.platform()}")
        safe_log(f"Python: {sys.version.split()[0]}")
        safe_log(f"Virtual Environment: {'Yes' if self.results['virtual_env'] else 'No'}")
        safe_log(f"CUDA Available: {'Yes' if self.results['cuda_available'] else 'No'}")
        safe_log(f"GPUs Detected: {len(self.results['gpu_info'])}")
        
        for gpu in self.results['gpu_info']:
            safe_log(f"  - GPU {gpu['id']}: {gpu['name']} ({gpu['memory_mb']} MB)")
        
        safe_log(f"Required Packages: {'All installed' if self.results['packages_installed'] else 'Missing some'}")
        
        # Save report to file
        report_data = {
            'timestamp': str(pd.Timestamp.now()) if 'pd' in globals() else 'now',
            'platform': platform.platform(),
            'python_version': sys.version,
            'results': self.results
        }
        
        with open('logs/environment_report.json', 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        safe_log("[OK] Report saved to logs/environment_report.json")

def main():
    """Main execution function"""
    safe_log("=== RAG SYSTEM ENVIRONMENT CHECKER ===")
    
    checker = EnvironmentChecker()
    
    # Run all checks
    checker.check_python_version()
    checker.check_virtual_environment() 
    checker.check_cuda_and_gpu()
    
    # Install packages if needed
    if not checker.check_required_packages():
        safe_log("Some packages are missing. Installing...")
        if checker.install_missing_packages():
            safe_log("[OK] Package installation completed")
            # Re-check packages
            checker.check_required_packages()
        else:
            safe_log("[ERROR] Package installation failed", "ERROR")
    
    # Create project structure
    checker.create_project_structure()
    
    # Generate final report
    checker.generate_report()
    
    # Summary
    if all([
        checker.results['python_version'],
        checker.results['packages_installed']
    ]):
        safe_log("[OK] Environment setup completed successfully!")
        safe_log("=== NEXT STEPS ===")
        safe_log("1. Review the .env file and adjust settings if needed")
        safe_log("2. Initialize the database: python scripts/init_db.py")
        safe_log("3. Start the API server: uvicorn rag_system.api_service.main:app --reload")
        
        if checker.results['cuda_available']:
            safe_log("[INFO] CUDA detected - GPU acceleration will be used")
        else:
            safe_log("[INFO] No CUDA - will use CPU (still fast for your dataset size)")
    else:
        safe_log("[ERROR] Environment setup incomplete. Check logs for details.", "ERROR")

if __name__ == "__main__":
    main()