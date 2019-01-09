#!/bin/bash
source secrets.sh
docker run -it -p 80:5000 \
	-v /Users/maayanlab/Documents/Zichen_Projects/scv/data:/my_application/data \
	-e ENTER_POINT="/embed" \
	-e MONGOURI=$MONGOURI \
	-e GOOGLE_APPLICATION_CREDENTIALS="$GOOGLE_APPLICATION_CREDENTIALS" \
	-e APPLICATION_DEFAULT_CREDENTIALS="$APPLICATION_DEFAULT_CREDENTIALS" \
	-e GCLOUD_PROJECT="$GCLOUD_PROJECT" \
	maayanlab/scv:slim-r
	