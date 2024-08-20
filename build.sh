#/bin/bash

pyinstaller setup-tool/evotool.py --onedir

cp -r diagnostics dist/evotool
cp -r calibration dist/evotool

cd dist
zip -r evotool.zip evotool
cd .. 
