@echo off
title BioNex - Autonomous Biomedical Waste System
echo =====================================================================
echo           BIONEX: BIOMEDICAL WASTE AMR ROBOTIC SYSTEM
echo =====================================================================
echo.
echo Starting BioNex FastAPI Server & Web Portal...
echo Local URL:     http://127.0.0.1:8000
echo Network URL:   http://192.168.1.18:8000
echo API Docs:      http://127.0.0.1:8000/docs
echo.
echo Launching default web browser...
start "" "http://127.0.0.1:8000"
echo.
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
pause
