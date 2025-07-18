#!/bin/bash

######### Deactivating active environment
if [[ "$VIRTUAL_ENV" != "" ]]
then
 echo "=====> Deactivating active environment."
 deactivate
fi

if [ -d "${CWD}/.venv" ]; then
 echo "=====> Removing old environment."
 rm -rf .venv
fi

######### Active environment
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

######### Install dependencies
pip3 install -r requirements.txt

