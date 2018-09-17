#!/bin/bash
source secrete.sh
docker run -it -p 80:5000 \
	-e ENTER_POINT="/embed" \
	-e MONGOURI=$MONGOURI \
	-v /Users/maayanlab/Documents/Zichen_Projects/scv/data:/my_application/data \
	maayanlab/scv:slim-r
