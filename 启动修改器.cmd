@echo off
pushd "%~dp0"
python save_editor.py
if errorlevel 1 pause
popd
