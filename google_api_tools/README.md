# Google API Tools

A collection of tools for interacting with Google APIs, including YouTube and Google Calendar.

## Tools Included

- **YouTube Manager**: Manage YouTube comments with AI-assisted responses
- **Google Calendar Report**: Generate reports from Google Calendar data

## Project Structure

```
google_api_tools/
├── common/                  # Shared utilities and helpers
│   ├── __init__.py
│   ├── auth.py              # Common authentication functions
│   └── config.py            # Common configuration handling
│
├── youtube_manager/         # YouTube management tools
│   ├── __init__.py
│   ├── ai_responder.py      # AI-based comment response generation
│   ├── data_processor.py    # Process YouTube data
│   ├── youtube_app.py       # Main YouTube application
│   └── README.md            # YouTube manager documentation
│
├── gcal_report/             # Google Calendar reporting tools
│   ├── __init__.py
│   ├── gcal_app.py          # Main Calendar application
│   ├── setup_credentials.py # Setup for Calendar credentials
│   └── README.md            # Calendar tool documentation
│
├── scripts/                 # Utility scripts
│   ├── setup_env.py         # Environment setup
│   └── clear_duplicated.sh  # Maintenance script
│
├── requirements.txt         # Project dependencies
└── README.md                # Main project documentation
```

## Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up credentials for the specific API you want to use
   - For YouTube: Follow instructions in `youtube_manager/README.md`
   - For Google Calendar: Follow instructions in `gcal_report/README.md`

## Usage

See the README files in each tool's directory for specific usage instructions.
