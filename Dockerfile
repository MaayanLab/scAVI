FROM ubuntu:18.04

# Install system dependencies
ENV R_BASE_VERSION 3.5.3
RUN set -x \
	&& echo "Preparing system..." \
	&& apt-get update -y \
	&& apt-get install -y \
		apt-transport-https \
		ca-certificates \
		dirmngr \
		gnupg2 \
		software-properties-common \
		tzdata \
	&& echo "Applying timezone fix..." \
	&& ln -fs /usr/share/zoneinfo/America/New_York /etc/localtime \
	&& dpkg-reconfigure --frontend noninteractive tzdata \
	&& echo "Trusting and adding R-repository..." \
	&& apt-key adv --keyserver keyserver.ubuntu.com --recv-keys '51716619E084DAB9' \
	&& add-apt-repository 'deb https://cloud.r-project.org/bin/linux/ubuntu bionic-cran35/' \
	&& echo "Installing system dependencies..." \
	&& apt-get update -y \
	&& apt-get upgrade -y \
	&& apt-get install -y \
		aptitude \
		build-essential \
		default-libmysqlclient-dev \
		gfortran \
		libatlas-base-dev \
		libcurl4-openssl-dev \
		libicu60 \
		libjpeg8 \
		libxml2-dev \
		r-base \
		r-base-core \
		r-base-dev \
    python-pip \
    python2.7 \
    python2.7-dev

# Dependencies for monocle
RUN set -x \
	&& echo "Installing R dependencies..." \
	&& R -e 'install.packages(c("reticulate", "DDRTree", "XML", "RCurl", "BiocManager"), repos = "https://cran.rstudio.com/")' \
	&& R -e 'BiocManager::install(c("monocle"))'

# Install required python packages
ADD requirements.txt /requirements.txt
RUN set -x \
	&& echo "Installing python dependencies..." \
	&& pip2 install -r requirements.txt \
	&& rm /requirements.txt

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
