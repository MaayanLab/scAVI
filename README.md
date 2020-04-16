# scAVI
scAVI is a web-based platform developed to enable users to analyze and visualize published and not published single cell RNA sequencing (scRNA-seq) datasets with state-of-the-art algorithms and visualization methods.

The scAVI platform supports the analysis and visualization of 463 publicly available scRNA-seq studies from GEO covering 194,653 single cells/samples. Analyses are provided as 463 dedicated landing pages and Jupyter Notebook reports for each study.

## Deploying

### Environment
scAVI depends on several external elements including:
- biojupies notebook generator
  - google cloud storage of notebooks
  - mysql for registration of notebooks
- scavi visualization
  - mongodb for pca/coords & metadata

The `Dockerfile` has detailed directions about setting up a system with the necessary R & python dependencies while the `docker-compose.yml` demonstrates how scavi can connect to the various external components. More likely, you would run those databases on the cloud and configure them.

The `.env.example` file has some example values, it can be copied over to `.env` and modified with the credentials and paths you use in your own application prior to using the docker-compose.

For help setting up scavi for yourself it is recommended that you contact us for further direction.

### NPM
We use nodejs for some of the UI development, for this purpose the npm package manager has a `package.json` file which identifies all necessary dependencies. Assuming you already have npm installed, this is a simple `npm install` command. For more information on npm, including installing it, please consult the [npm docs](https://docs.npmjs.com/).

### Docker
We use `Dockerfile` and `docker-compose.yml` to document the process of constructing a complete virtual system capable of running this application. This includes R and python installations; the docker-compose goes a level higher and documents how scavi interacts with external databases. For more information on using docker-compose, please consult the [docker-compose documentation](https://docs.docker.com/compose/)..

```bash
# Ensure you install npm dependencies in the static directory prior to building the dockerfile
cd static && npm i
# Then build the dockerfile
docker-compose build scavi
# And run
docker-compose up scavi
# Or deploy
docker-compose push scavi
```
