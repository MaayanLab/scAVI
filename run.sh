#!/bin/bash
export ENTER_POINT='/embed'
source secrets.sh
echo $MONGOURI
# export debug='0'
python app.py
unset ENTER_POINT
unset MONGOURI
