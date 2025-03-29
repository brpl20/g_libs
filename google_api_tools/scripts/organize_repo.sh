#!/bin/bash
# Script to organize the repository structure

# Create directory structure
mkdir -p google_api_tools/common
mkdir -p google_api_tools/youtube_manager
mkdir -p google_api_tools/gcal_report
mkdir -p google_api_tools/scripts

# Move YouTube manager files
cp yt_manager/ai_responder.py google_api_tools/youtube_manager/
cp yt_manager/config.py google_api_tools/youtube_manager/
cp yt_manager/data_processor.py google_api_tools/youtube_manager/
cp yt_manager/youtube_app.py google_api_tools/youtube_manager/
cp yt_manager/README.md google_api_tools/youtube_manager/
cp yt_manager/clear_duplicated.sh google_api_tools/scripts/
cp yt_manager/setup_env.py google_api_tools/scripts/

# Move Google Calendar report files
cp gcal_report/gcal_app.py google_api_tools/gcal_report/
cp gcal_report/setup_credentials.py google_api_tools/gcal_report/
cp gcal_report/README.md google_api_tools/gcal_report/

echo "Repository structure organized successfully!"
