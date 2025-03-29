# Use an official Python runtime as a parent image
#FROM python:3.11-slim
FROM alibaba-cloud-linux-3-registry.cn-hangzhou.cr.aliyuncs.com/alinux3/python:3.11.1
# Set the working directory in the container
WORKDIR /app

#RUN apt-get update && apt-get install -y build-essential libssl-dev libffi-dev python3-dev
RUN yum update -y && yum install -y gcc make libssl-devel libffi-devel python3-devel


# Copy the requirements file into the container
COPY requirements.txt .

# Install Python packages specified in requirements.txt
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose the port the app runs on
EXPOSE 80

# Start the Django application
CMD ["python3", "manage.py", "runserver", "0.0.0.0:80"]