FROM python:2.7

# Get pip and install numpy/scipy dependencies
RUN apt-get update && apt-get install -y build-essential gfortran libatlas-base-dev libmysqlclient-dev

# Update pip
RUN pip install --upgrade pip

# Install required python packages
RUN pip install \
	pandas==0.20.1\
	requests==2.6.2\
	flask==0.12\
	scipy==0.15.1\
	scikit-learn==0.19\
	xlrd

# Copy the application folder inside the container
ADD . /my_application

# Expose ports
EXPOSE 5000

# Set the default directory where CMD will execute
WORKDIR /my_application

# Set the default command to execute    
# when creating a new container
CMD python app.py
