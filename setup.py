import os
import sys
import venv
import platform
import subprocess
from setuptools import setup, find_packages
from setuptools.command.install import install

# Read the README file for the long description
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

class CustomInstallCommand(install):
    def run(self):
        # Create virtual environment if it doesn't exist
        venv_dir = "env"
        if not os.path.exists(venv_dir):
            print(f"Creating virtual environment in {venv_dir}...")
            venv.create(venv_dir, with_pip=True)
            
            # Get the path to the Python executable in the virtual environment
            if platform.system() == "Windows":
                python_executable = os.path.join(venv_dir, "Scripts", "python.exe")
                pip_executable = os.path.join(venv_dir, "Scripts", "pip.exe")
                activate_cmd = f".\\{venv_dir}\\Scripts\\activate"
                ps_cmd = f".\\{venv_dir}\\Scripts\\Activate.ps1"
            else:
                python_executable = os.path.join(venv_dir, "bin", "python")
                pip_executable = os.path.join(venv_dir, "bin", "pip")
                activate_cmd = f"source {venv_dir}/bin/activate"

            # Install dependencies in the virtual environment
            print("Installing dependencies in virtual environment...")
            requirements = [
                "pyaudio",
                "PySide6",
                "keyboard",
                "faster-whisper",
                "ctranslate2"
            ]
            
            for req in requirements:
                print(f"Installing {req}...")
                try:
                    subprocess.check_call([pip_executable, "install", req])
                except subprocess.CalledProcessError as e:
                    print(f"Warning: Failed to install {req}. Error: {e}")
                    continue
            
            # Print activation instructions
            if platform.system() == "Windows":
                print("\nVirtual environment created! To activate it:")
                print(f"- Command Prompt: {activate_cmd}")
                print(f"- PowerShell: {ps_cmd}")
            else:
                print("\nVirtual environment created! To activate it:")
                print(f"Run: {activate_cmd}")

        # Run the standard install
        install.run(self)

setup(
    name="fast_whisper_v2",
    version="0.1.0",
    author="Tobias R",
    description="Fast Whisper-v2 is a simple and user-friendly application that uses Faster Whisper for fast and accurate transcription. It provides an easy way to handle audio transcription tasks.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "pyaudio",
        "PySide6",
        "keyboard",
        "faster-whisper",
        "ctranslate2",
    ],
    entry_points={
        "console_scripts": [
            "fast-whisper=main:main",
        ]
    },
    extras_require={
        "dev": [
            "pytest",
            "flake8",
        ]
    },
    package_data={
        "": ["*.json", "*.md", "*.css"],
    },
    data_files=[
        ("config", ["config.json"]),
    ],
    zip_safe=False,
    cmdclass={
        'install': CustomInstallCommand,
    }
)