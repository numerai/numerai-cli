FROM r-base:latest

# install dev tools
RUN apt-get update -y && apt-get install -y \
    build-essential \
    libcurl4-gnutls-dev \
    libxml2-dev \
    libssl-dev
RUN R -e "install.packages('devtools', dependencies=TRUE)"

# copy over install script and install R packages
ADD install_packages.R .
RUN Rscript ./install_packages.R

# copy everything else
ADD . .

# These arguments are passed in by the `numerai` tool
ARG NUMERAI_PUBLIC_ID
ENV NUMERAI_PUBLIC_ID=$NUMERAI_PUBLIC_ID

ARG NUMERAI_SECRET_KEY
ENV NUMERAI_SECRET_KEY=$NUMERAI_SECRET_KEY

ARG MODEL_ID
ENV MODEL_ID=$MODEL_ID

# Replace this with the name of your script
CMD [ "Rscript", "./main.R" ]
