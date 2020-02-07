# scAVI
scAVI is a web-based platform developed to enable users to analyze and visualize published and not published single cell RNA sequencing (scRNA-seq) datasets with state-of-the-art algorithms and visualization methods.

The scAVI platform supports the analysis and visualization of 463 publicly available scRNA-seq studies from GEO covering 194,653 single cells/samples. Analyses are provided as 463 dedicated landing pages and Jupyter Notebook reports for each study.

## Deploying
```bash
# Ensure you install npm dependencies in the static directory prior to building the dockerfile
cd static && npm i
# Then build the dockerfile
docker-compose build scavi
# And deploy
docker-compose push scavi
```
