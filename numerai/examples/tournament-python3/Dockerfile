# Provides us a working Python 3 environment.
FROM python:3.7

# We then add the requirements.txt file, and pip install every requirement from it.
# The `ADD [source] [destination]` command will take a file from the source directory on your computer
# and copy it over to the destination directory in the Docker container.
ADD requirements.txt .
RUN pip install -r requirements.txt

# Now, add EVERYTHING in the current directory.
# (including your code, compiled files, and serialized models)
ADD . .

# These are docker arguments that `numerai node deploy/test` will always pass into docker.
# They are then set in your environment, so that you can access them from your script like so:
    # import os
    # public_id = os.environ["NUMERAI_PUBLIC_ID"]
    # secret_key = os.environ["NUMERAI_SECRET_KEY"]
ARG NUMERAI_PUBLIC_ID
ENV NUMERAI_PUBLIC_ID=$NUMERAI_PUBLIC_ID

ARG NUMERAI_SECRET_KEY
ENV NUMERAI_SECRET_KEY=$NUMERAI_SECRET_KEY

# This sets the default command to run your docker container.
# It runs by default in the cloud and when running `numerai node test`.
# This is overridden when using `numerai node test --command [COMMAND]`.
CMD [ "python", "./predict.py" ]
