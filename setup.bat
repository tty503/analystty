@echo off

echo Verifying the existence of a virtual environment...
if not exist venv\Scripts\activate (
  echo Creating a virtual environment
  py -m venv venv
)

echo Enabling the virtual environment.
venv\Scripts\activate

echo Installing dependencies...
pip install -r requirements.txt

echo Installing project...
py setup.py install

echo Done!