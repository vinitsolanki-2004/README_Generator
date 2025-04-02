**README GENERATOR**
================

**Project Description**
---------------------

My Project is a Python-based tool that utilizes the Groq API to analyze directories and generate comprehensive README files. The project leverages the Streamlit library to provide an interactive interface for users to input directory paths and retrieve detailed file information.

**Badges**
----------

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.10.0+-orange.svg)](https://streamlit.io/)
[![Groq API](https://img.shields.io/badge/Groq%20API-v1-green.svg)](https://api.groq.com/)

**Installation**
--------------

To install the project, follow these steps:

1. Clone the repository: `git clone https://github.com/vinitsolanki-2004/README_Generator.git`
2. Install the required dependencies: `pip install -r requirements.txt`

**Usage**
-----

To use the project, follow these steps:

1. Run the application: `python app.py`
2. Input the directory path you want to analyze in the Streamlit interface
3. Click the "Analyze Directory" button to retrieve file information

**Features**
---------

* Analyze directory structures and collect file information
* Utilize the Groq API to generate comprehensive README files
* Interactive interface using Streamlit for easy user input

**Dependencies**
------------

* Python 3.9+
* Streamlit 1.10.0+
* Groq API v1
* `requests` library for API requests
* `pathlib` library for file path manipulation
* `dotenv` library for environment variable management

**Contributing**
------------

Contributions are welcome! To contribute to the project, follow these steps:

1. Fork the repository: `git fork https://github.com/vinitsolanki-2004/README_Generator.git`
2. Create a new branch: `git branch feature/new-feature`
3. Make changes and commit them: `git commit -m "Added new feature"`
4. Create a pull request: `git push origin feature/new-feature`

**License**
-------

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

**Table of Contents**
-------------------

* [Project Description](#project-description)
* [Badges](#badges)
* [Installation](#installation)
* [Usage](#usage)
* [Features](#features)
* [Dependencies](#dependencies)
* [Contributing](#contributing)
* [License](#license)

**Code Snippet**
----------------

Here's a code snippet from the `app.py` file:
```python
class GroqReadmeGenerator:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self.model = "llama3-70b-8192"  # Default Groq model
```
