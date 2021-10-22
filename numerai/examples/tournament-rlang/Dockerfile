# Provides us a working R lang environment.
FROM r-base:latest

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

# install dev tools
RUN apt-get update -y && apt-get install -y \
    build-essential \
    libcurl4-gnutls-dev \
    libxml2-dev \
    libssl-dev
RUN R -e "install.packages('devtools', dependencies=TRUE)"

# We then add the install_packages.R file, and install every requirement from it.
# The `ADD [source] [destination]` command will take a file from the source directory on your computer
# and copy it over to the destination directory in the Docker container.
ADD $SRC_PATH/install_packages.R .
RUN Rscript ./install_packages.R

# Now, add everything in the source code directory.
# (including your code, compiled files, serialized models, everything...)
ADD $SRC_PATH .

# This sets the default command to run your docker container.
# It runs by default in the cloud and when running `numerai node test`.
# This is overridden when using `numerai node test --command [COMMAND]`.
CMD [ "Rscript", "./main.R" ]
