#!/usr/bin/env python
import os
import subprocess
import sys
import time
import webbrowser
import platform

def check_requirements():
    """Check if required packages are installed and install them if missing."""
    required_packages = ['flask', 'flask-cors', 'python-dotenv', 'google-generativeai']
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✓ {package} is installed")
        except ImportError:
            print(f"Installing {package}...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
            print(f"✓ {package} has been installed")
    
    print("All requirements satisfied!")

def check_api_key():
    """Check if the Gemini API key is set in the .env file."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    
    if not os.path.exists(env_path):
        print("⚠️ .env file not found!")
        api_key = input("Please enter your Gemini API key: ")
        if api_key:
            with open(env_path, 'w') as f:
                f.write(f"# Gemini API Key\nGEMINI_API_KEY={api_key}\n")
            print("✓ API key saved to .env file")
        else:
            print("❌ No API key provided. Exiting.")
            sys.exit(1)
    else:
        # Check if .env contains the API key
        with open(env_path, 'r') as f:
            content = f.read()
            if "GEMINI_API_KEY" not in content or "your_api_key_here" in content or "=" not in content:
                api_key = input("Please enter your Gemini API key: ")
                if api_key:
                    with open(env_path, 'w') as f:
                        f.write(f"# Gemini API Key\nGEMINI_API_KEY={api_key}\n")
                    print("✓ API key saved to .env file")
                else:
                    print("❌ No API key provided. Exiting.")
                    sys.exit(1)
            else:
                print("✓ API key found in .env file")

def start_server():
    """Start the Gemini Food Analyzer server."""
    print("\nStarting Gemini Food Analyzer server...")
    
    # Determine which Python command to use
    python_cmd = 'python' if platform.system() == 'Windows' else 'python3'
    
    # Start the server process
    server_process = subprocess.Popen(
        [python_cmd, 'gemini_food_analyzer.py'],
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    
    # Wait a moment for the server to start
    print("Waiting for server to start...")
    time.sleep(3)
    
    return server_process

def open_web_interface():
    """Open the web interface in the default browser."""
    # Get the absolute path to the HTML file
    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gemini_food_tester.html')
    
    # Format as URL
    if platform.system() == 'Windows':
        file_url = 'file:///' + html_path.replace('\\', '/')
    else:
        file_url = 'file://' + html_path
    
    print("\nOpening web interface...")
    try:
        webbrowser.open(file_url)
        print("✓ Web interface opened in browser")
    except Exception as e:
        print(f"❌ Failed to open web interface: {e}")
        print(f"Please open manually: {html_path}")

def main():
    """Main function to run the application."""
    print("=" * 50)
    print("🍲 Food Safety Analyzer")
    print("=" * 50)
    
    # Make sure we're in the right directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Check requirements
    check_requirements()
    
    # Check for API key
    check_api_key()
    
    # Start server
    server_process = start_server()
    
    # Open web interface
    open_web_interface()
    
    print("\n" + "=" * 50)
    print("The Food Safety Analyzer is now running!")
    print("- Web interface is open in your browser")
    print("- API server is running at http://localhost:5000")
    print("=" * 50)
    print("\nPress Ctrl+C to stop the server and exit")
    
    try:
        # Keep the script running
        server_process.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server_process.terminate()
        print("Goodbye! 👋")

if __name__ == "__main__":
    main() 