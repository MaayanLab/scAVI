FROM python:2.7-slim

# Install numpy/scipy dependencies
RUN apt-get update && apt-get install -y build-essential gfortran libatlas-base-dev \
	libxml2-dev \
	aptitude \
	libcurl4-openssl-dev \
	default-libmysqlclient-dev

# Install R 3.5
RUN echo 'deb http://cran.rstudio.com/bin/linux/debian stretch-cran35/' >> /etc/apt/sources.list 
# RUN apt-get install -y dirmngr && apt-key adv --keyserver keys.gnupg.net --recv-key 'E19F5F87128899B192B1A2C2AD5F960A256A04AF'
RUN apt-get update && apt-get install -y  --allow-unauthenticated r-base

# Install required python packages
RUN pip install \
	pandas==0.21.0\
	gevent==1.2.2\
	Flask==0.12.2\
	Flask-PyMongo==0.5.1\
	Flask-SocketIO==2.9.4\
	h5py==2.9.0\
	requests==2.18.4\
	scipy==1.0.0\
	scikit-learn==0.19.1\
	google-cloud-storage==1.13.2\
	flask_sqlalchemy==2.0\
	MySQL-python\
	flask_cors==2.0.1

# Dependencies for monocle
RUN R -e 'install.packages(c("reticulate", "DDRTree", "XML", "RCurl"), repos = "https://cran.rstudio.com/")'
RUN R -e 'source("http://bioconductor.org/biocLite.R"); biocLite("monocle");'

RUN pip install rpy2==2.8.6

# Copy the application folder inside the container
ADD . /my_application

# Expose ports
EXPOSE 5000

# Set the default directory where CMD will execute
WORKDIR /my_application
# Set up connection to google cloud storage
RUN mkdir -p .config/gcloud
# Set the default command to execute    
# when creating a new container
CMD echo $APPLICATION_DEFAULT_CREDENTIALS > $GOOGLE_APPLICATION_CREDENTIALS && python app.py
