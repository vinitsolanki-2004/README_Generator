import os
import json
import requests
import streamlit as st
from pathlib import Path
import tempfile
import shutil
import zipfile
import base64
import time
import glob
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API keys from environment variables
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

class GroqReadmeGenerator:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self.model = "llama3-70b-8192"  # Default Groq model
    
    def analyze_directory(self, directory_path):
        """
        Scan the directory and collect information about files
        """
        st.write(f"Scanning directory: {directory_path}")
        
        project_name = os.path.basename(os.path.abspath(directory_path))
        file_info = []
        file_count = 0
        ignored_dirs = ['.git', 'node_modules', 'venv', '__pycache__', '.idea', '.vscode']
        ignored_extensions = ['.pyc', '.class', '.o', '.so', '.dll', '.exe']
        
        for root, dirs, files in os.walk(directory_path):
            # Skip ignored directories
            dirs[:] = [d for d in dirs if d not in ignored_dirs and not d.startswith('.')]
            
            for file in files:
                # Skip hidden and ignored extension files
                if file.startswith('.') or any(file.endswith(ext) for ext in ignored_extensions):
                    continue
                
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, directory_path)
                
                # Skip large files (>100KB for code analysis)
                if os.path.getsize(file_path) > 100 * 1024:
                    file_info.append({
                        "path": rel_path,
                        "size": os.path.getsize(file_path),
                        "content": "File too large to include in analysis"
                    })
                    continue
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        file_info.append({
                            "path": rel_path,
                            "size": os.path.getsize(file_path),
                            "content": content
                        })
                        file_count += 1
                except Exception as e:
                    # Handle binary files or encoding issues
                    file_info.append({
                        "path": rel_path,
                        "size": os.path.getsize(file_path),
                        "content": "Unable to read file content"
                    })
        
        st.write(f"Found {file_count} readable files")
        return project_name, file_info
    
    def process_individual_files(self, files_dict, project_name):
        """
        Process individually uploaded files
        """
        file_info = []
        
        for file_path, content in files_dict.items():
            file_info.append({
                "path": file_path,
                "size": len(content),
                "content": content
            })
        
        return project_name, file_info
    
    def process_github_url(self, github_url, auth_token=None):
        """
        Process a GitHub repository URL
        Format: https://github.com/username/repo
        """
        # Extract username and repo from URL
        parts = github_url.rstrip('/').split('/')
        if len(parts) < 5 or parts[2] != 'github.com':
            raise ValueError("Invalid GitHub URL format. Please use https://github.com/username/repo")
        
        username = parts[3]
        repo = parts[4]
        
        # Create API URL for repo contents
        api_url = f"https://api.github.com/repos/{username}/{repo}/contents"
        
        headers = {}
        if auth_token:
            headers['Authorization'] = f"token {auth_token}"
        
        # Create a temporary directory
        with tempfile.TemporaryDirectory() as tmpdirname:
            self._download_github_contents(api_url, tmpdirname, headers)
            project_name = repo
            return self.analyze_directory(tmpdirname)
    
    def _download_github_contents(self, url, path, headers, depth=0):
        """
        Recursively download GitHub repository contents
        """
        if depth > 5:  # Limit recursion depth
            return
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            contents = response.json()
            
            for item in contents:
                if item['type'] == 'file':
                    # Skip large files
                    if item.get('size', 0) > 100 * 1024:
                        continue
                    
                    # Skip binary files and known non-readable extensions
                    _, ext = os.path.splitext(item['name'])
                    if ext.lower() in ['.exe', '.dll', '.so', '.pyc', '.class', '.o']:
                        continue
                    
                    # Download file content
                    file_response = requests.get(item['download_url'], headers=headers)
                    if file_response.status_code == 200:
                        file_path = os.path.join(path, item['name'])
                        os.makedirs(os.path.dirname(file_path), exist_ok=True)
                        with open(file_path, 'w', encoding='utf-8') as f:
                            try:
                                f.write(file_response.text)
                            except UnicodeEncodeError:
                                # Skip files that can't be encoded
                                pass
                
                elif item['type'] == 'dir':
                    # Create directory and download its contents
                    dir_path = os.path.join(path, item['name'])
                    os.makedirs(dir_path, exist_ok=True)
                    self._download_github_contents(item['url'], dir_path, headers, depth + 1)
        
        except Exception as e:
            st.warning(f"Error downloading GitHub contents: {str(e)}")
    
    def generate_directory_structure(self, file_info):
        """
        Create a directory tree structure from file information
        """
        paths = [file["path"] for file in file_info]
        structure = {}
        
        for path in sorted(paths):
            parts = path.split('/')
            current = structure
            
            for i, part in enumerate(parts):
                if i == len(parts) - 1:  # File
                    if 'files' not in current:
                        current['files'] = []
                    current['files'].append(part)
                else:  # Directory
                    if 'dirs' not in current:
                        current['dirs'] = {}
                    if part not in current['dirs']:
                        current['dirs'][part] = {}
                    current = current['dirs'][part]
        
        # Convert to formatted string
        def format_structure(node, prefix=""):
            result = ""
            if 'dirs' in node:
                for name, subdir in sorted(node['dirs'].items()):
                    result += f"{prefix}📂 {name}/\n"
                    result += format_structure(subdir, prefix + "  ")
            if 'files' in node:
                for file in sorted(node['files']):
                    result += f"{prefix}📄 {file}\n"
            return result
        
        return format_structure(structure)
    
    def identify_key_files(self, file_info):
        """
        Identify important files in the project
        """
        important_files = {
            'main': [],
            'config': [],
            'requirements': [],
            'tests': [],
            'documentation': [],
            'license': []
        }
        
        for file in file_info:
            path = file["path"]
            filename = os.path.basename(path).lower()
            
            # Main application files
            if filename in ['main.py', 'app.py', 'index.js', 'app.js', 'server.js', 'index.html']:
                important_files['main'].append(path)
            
            # Configuration files
            if filename in ['config.json', 'package.json', '.env.example', 'dockerfile', 'docker-compose.yml']:
                important_files['config'].append(path)
            
            # Requirement files
            if filename in ['requirements.txt', 'package.json', 'pipfile', 'poetry.lock']:
                important_files['requirements'].append(path)
            
            # Test files
            if 'test' in filename or filename.startswith('test_'):
                important_files['tests'].append(path)
            
            # Documentation
            if filename in ['readme.md', 'contributing.md', 'changelog.md', 'documentation.md']:
                important_files['documentation'].append(path)
            
            # License
            if 'license' in filename:
                important_files['license'].append(path)
        
        return important_files
    
    def get_file_contents(self, file_info, key_files):
        """
        Retrieve content from key files for AI analysis
        """
        content_dict = {}
        
        # Collect all important files for analysis
        all_key_files = []
        for category, files in key_files.items():
            all_key_files.extend(files)
        
        for file in file_info:
            if file["path"] in all_key_files:
                content_dict[file["path"]] = file["content"]
        
        return content_dict
    
    def call_groq_api(self, project_name, directory_structure, key_files, file_contents):
        """
        Call Groq API to generate README content
        """
        st.write("Calling Groq API to generate README...")
        
        # Format file content for prompt
        file_content_str = ""
        for path, content in file_contents.items():
            if len(content) > 1000:  # Limit large files to first 1000 chars
                content = content[:1000] + "... [content truncated]"
            file_content_str += f"\n--- {path} ---\n{content}\n"
        
        # Format key files for prompt
        key_files_str = ""
        for category, files in key_files.items():
            if files:
                key_files_str += f"\n{category.upper()}:\n"
                for file in files:
                    key_files_str += f"- {file}\n"
        
        # Craft the prompt
        prompt = f"""
You are an expert developer tasked with creating a professional GitHub README.md file.

PROJECT INFORMATION:
- Project Name: {project_name}

DIRECTORY STRUCTURE:
```
{directory_structure}
```

KEY FILES:
{key_files_str}

I'm providing the content of key files to help you understand the project:
{file_content_str}

Based on this information, generate a comprehensive, professional README.md file in GitHub markdown format. Include:

1. Project title and description (summarize what the project does)
2. Badges for relevant languages/technologies
3. Installation instructions
4. Usage examples 
5. Features
6. Dependencies
7. Contributing guidelines
8. License information
9. A table of contents
10. Any other sections you deem appropriate based on the project content

Format the README.md file professionally with proper markdown formatting. Include code blocks with appropriate language syntax highlighting where relevant. Focus on clarity and usefulness.
"""

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 4000
        }

        try:
            with st.spinner("Generating README with Groq AI..."):
                response = requests.post(
                    self.base_url,
                    headers=self.headers,
                    data=json.dumps(payload)
                )
                response.raise_for_status()
                result = response.json()
                return result["choices"][0]["message"]["content"]
        except Exception as e:
            st.error(f"Error calling Groq API: {e}")
            if 'response' in locals() and hasattr(response, 'text'):
                st.error(f"API response: {response.text}")
            return f"# {project_name}\n\nError generating README: {str(e)}"

# Functions for Streamlit file handling
def extract_zip(zip_file):
    """Extract zip file to a temporary directory"""
    with tempfile.TemporaryDirectory() as tmpdirname:
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(tmpdirname)
        return tmpdirname

def get_download_link(content, filename="README.md"):
    """Generate a download link for the README file"""
    b64 = base64.b64encode(content.encode()).decode()
    href = f'<a href="data:file/txt;base64,{b64}" download="{filename}">Download {filename}</a>'
    return href

def main():
    st.set_page_config(
        page_title="Groq README Generator",
        page_icon="📝",
        layout="wide"
    )
    
    st.title("📝 Groq README Generator")
    st.write("""
    Generate professional GitHub README.md files using Groq's AI.
    Choose one of the input methods below to analyze your project.
    """)
    
    # Sidebar configuration
    with st.sidebar:
        st.header("Configuration")
        api_key = st.text_input("Groq API Key", type="password", help="Your Groq API key")
        
        st.subheader("Model Selection")
        model_options = ["llama3-70b-8192", "llama3-8b-8192", "mixtral-8x7b-32768"]
        selected_model = st.selectbox("Choose Groq Model", model_options)
        
        st.markdown("---")
        st.markdown("### About")
        st.markdown("This tool scans your project files and uses Groq's AI to generate a comprehensive README.md file.")
        st.markdown("⚠️ Your files are processed locally and only key file contents are sent to Groq API.")
    
    # Project name field
    custom_project_name = st.text_input("Custom Project Name (Optional)", 
                                     help="By default, we'll use the directory name or repository name")
    
    # Main content area with tabs for different input methods
    tab1, tab2, tab3, tab4 = st.tabs(["ZIP Upload", "Multiple Files", "GitHub URL", "Local Directory"])
    
    # Store the input method and data
    input_method = None
    input_data = None
    
    # Tab 1: ZIP Upload
    with tab1:
        st.header("Upload ZIP")
        st.write("Upload your project as a ZIP file")
        zip_file = st.file_uploader("Upload your project as a ZIP file", type="zip")
        if st.button("Process ZIP", key="process_zip", disabled=(not zip_file or not api_key)):
            input_method = "zip"
            input_data = zip_file
    
    # Tab 2: Individual Files
    with tab2:
        st.header("Upload Individual Files")
        st.write("Upload key project files individually")
        uploaded_files = st.file_uploader("Upload project files", type=["py", "js", "html", "css", "json", "md", "txt"], accept_multiple_files=True)
        
        if uploaded_files:
            st.write(f"Uploaded {len(uploaded_files)} files:")
            for file in uploaded_files:
                st.write(f"- {file.name}")
        
        if st.button("Process Files", key="process_files", disabled=(not uploaded_files or not api_key)):
            # Read file contents
            files_dict = {}
            for file in uploaded_files:
                try:
                    file_content = file.read().decode("utf-8")
                    files_dict[file.name] = file_content
                except UnicodeDecodeError:
                    st.warning(f"Skipping binary file: {file.name}")
            
            input_method = "files"
            input_data = files_dict
    
    # Tab 3: GitHub URL
    with tab3:
        st.header("GitHub Repository")
        st.write("Enter a public GitHub repository URL")
        github_url = st.text_input("GitHub URL (e.g., https://github.com/username/repo)")
        github_token = st.text_input("GitHub Personal Access Token (Optional, for private repos)", type="password")
        
        if st.button("Process GitHub Repo", key="process_github", disabled=(not github_url or not api_key)):
            input_method = "github"
            input_data = (github_url, github_token if github_token else None)
    
    # Tab 4: Local Directory Path (when running locally)
    with tab4:
        st.header("Local Directory")
        st.write("Specify a local directory path on your machine (only works when running Streamlit locally)")
        local_path = st.text_input("Directory Path")
        
        if st.button("Process Directory", key="process_dir", disabled=(not local_path or not api_key or not os.path.isdir(local_path))):
            input_method = "directory"
            input_data = local_path
    
    # Process the input if any method was selected
    if input_method and api_key:
        generator = GroqReadmeGenerator(api_key)
        generator.model = selected_model
        
        progress_bar = st.progress(0)
        status_placeholder = st.empty()
        results_placeholder = st.empty()
        
        try:
            # Process based on input method
            if input_method == "zip":
                # Save the uploaded zip file to a temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
                    tmp_file.write(input_data.getvalue())
                    tmp_file_path = tmp_file.name
                
                # Extract the zip file
                status_placeholder.text("Extracting ZIP file...")
                project_dir = extract_zip(tmp_file_path)
                progress_bar.progress(20)
                
                # Analyze directory
                status_placeholder.text("Analyzing project files...")
                project_name_from_dir, file_info = generator.analyze_directory(project_dir)
                project_name = custom_project_name if custom_project_name else project_name_from_dir
                
                # Clean up the temporary file
                os.unlink(tmp_file_path)
            
            elif input_method == "files":
                # Process individual files
                status_placeholder.text("Processing uploaded files...")
                project_name = custom_project_name if custom_project_name else "My Project"
                project_name, file_info = generator.process_individual_files(input_data, project_name)
                progress_bar.progress(20)
            
            elif input_method == "github":
                # Process GitHub repository
                github_url, auth_token = input_data
                status_placeholder.text("Downloading GitHub repository...")
                try:
                    project_name_from_github, file_info = generator.process_github_url(github_url, auth_token)
                    project_name = custom_project_name if custom_project_name else project_name_from_github
                    progress_bar.progress(20)
                except Exception as e:
                    st.error(f"Error processing GitHub repository: {str(e)}")
                    st.stop()
            
            elif input_method == "directory":
                # Process local directory
                status_placeholder.text("Scanning local directory...")
                project_name_from_dir, file_info = generator.analyze_directory(input_data)
                project_name = custom_project_name if custom_project_name else project_name_from_dir
                progress_bar.progress(20)
            
            # Continue with the remaining steps
            status_placeholder.text("Generating directory structure...")
            directory_structure = generator.generate_directory_structure(file_info)
            progress_bar.progress(40)
            
            status_placeholder.text("Identifying key files...")
            key_files = generator.identify_key_files(file_info)
            progress_bar.progress(60)
            
            status_placeholder.text("Extracting file contents...")
            file_contents = generator.get_file_contents(file_info, key_files)
            progress_bar.progress(70)
            
            status_placeholder.text("Generating README with Groq AI...")
            readme_content = generator.call_groq_api(project_name, directory_structure, key_files, file_contents)
            progress_bar.progress(100)
            
            # Display the generated README
            status_placeholder.text("README generation complete!")
            
            with results_placeholder.container():
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    st.subheader("Preview")
                    st.markdown(readme_content)
                
                with col2:
                    st.subheader("Download & Copy")
                    st.markdown(get_download_link(readme_content), unsafe_allow_html=True)
                    
                    # Copy to clipboard option
                    st.text_area("Raw Markdown", readme_content, height=300)
                    
                    # Show key files analyzed
                    with st.expander("Key Files Analyzed"):
                        for category, files in key_files.items():
                            if files:
                                st.write(f"**{category.upper()}**")
                                for file in files:
                                    st.write(f"- {file}")
        
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()