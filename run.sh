#!/bin/bash
export ENTER_POINT='/embed'
source secrets0.sh
echo $MONGOURI
# rm logs/*.log
# cd scripts && python remove_test_upload_from_db.py && cd ..
export debug='1'
python app.py
unset ENTER_POINT
unset MONGOURI
