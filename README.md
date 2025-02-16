# DeepScope: AI-Powered Video Fact-Checking Service

DeepScope is an AI-generated fact-checking service that automatically analyzes video content, extracts claims, and verifies them against trusted sources. This system provides fact-checking capabilities through a FastAPI-based REST API.

## Features

- 🔍 AI-powered claim extraction from transcripts
- ✅ AI-generated fact-checking against multiple sources
- 🔄 Background processing with Firebase integration
- 📊 Comprehensive verdict aggregation
- 🚀 RESTful API interface

## Prerequisites

- Python 3.8+
- Firebase account and credentials
- OpenAI API key
- Google Fact Check API credentials

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/deepscope.git
cd deepscope
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file in the root directory with the following variables:
```
OPENAI_API_KEY=your_openai_api_key
GOOGLE_FACTCHECK_API_KEY=your_google_api_key
```

## Usage

1. Start the API server:
```bash
uvicorn src.main:app --reload
```

2. The API will be available at `http://localhost:8000`
3. Access the API documentation at `http://localhost:8000/docs`

```
deepscope/
├── src/
│   ├── chains/         # LangChain components
│   ├── models/         # Data models and schemas
│   ├── services/       # Business logic services
│   └── tests/          # Unit and integration tests
├── scripts/            # Utility scripts
└── docs/              # Documentation
```