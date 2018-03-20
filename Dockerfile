FROM python:2.7

# Get pip and install numpy/scipy dependencies
RUN apt-get update && apt-get install -y build-essential gfortran libatlas-base-dev libmysqlclient-dev

# Update pip
RUN pip install --upgrade pip

# Install required python packages
RUN pip install \
	pandas==0.20.1\
	gevent==1.2.2\
	Flask==0.12.2\
	Flask-PyMongo==0.5.1\
	Flask-SocketIO==2.9.4\
	h5py==2.7.1\
	requests==2.18.4\
	scipy==1.0.0\
	scikit-learn==0.19.1


# Copy the application folder inside the container
ADD . /my_application

# Expose ports
EXPOSE 5000

# Set the default directory where CMD will execute
WORKDIR /my_application

# Set the default command to execute    
# when creating a new container
CMD python app.py
