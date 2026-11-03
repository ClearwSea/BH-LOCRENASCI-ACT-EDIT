@echo off

pushd "%~dp0"

.build-env\Scripts\python.exe -m PyInstaller --noconfirm --onefile --windowed --name BH3-V1.9-Save-Editor --add-data "%~dp0stage_catalog.json;." --add-data "%~dp0templates;templates" --distpath dist --workpath build --specpath build save_editor.py

if errorlevel 1 pause

popd

