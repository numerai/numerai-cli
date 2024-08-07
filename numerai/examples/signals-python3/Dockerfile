# Provides us a working Python 3 environment.
FROM python:3.9

# These are docker arguments that `numerai node deploy/test` will always pass into docker.
# They are then set in your environment so that numerapi can access them when uploading submissions.
# You can also access them from your script like so:
# import os
# public_id = os.environ["NUMERAI_PUBLIC_ID"]
# secret_key = os.environ["NUMERAI_SECRET_KEY"]
ARG NUMERAI_PUBLIC_ID
ENV NUMERAI_PUBLIC_ID=$NUMERAI_PUBLIC_ID

ARG NUMERAI_SECRET_KEY
ENV NUMERAI_SECRET_KEY=$NUMERAI_SECRET_KEY

ARG MODEL_ID
ENV MODEL_ID=$MODEL_ID

ARG SRC_PATH
ENV SRC_PATH=$SRC_PATH

# We then add the requirements.txt file, and pip install every requirement from it.
# The `ADD [source] [destination]` command will take a file from the source directory on your computer
# and copy it over to the destination directory in the Docker container.
ADD $SRC_PATH/requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir

# Now, add everything in the source code directory.
# (including your code, compiled files, serialized models, everything...)
ADD $SRC_PATH .

# This sets the default command to run your docker container.
# It runs by default in the cloud and when running `numerai node test`.
# This is overridden when using `numerai node test --command [COMMAND]`.
CMD [ "python", "./predict.py" ]
