FROM r-base:latest

ADD install_packages.R .

# install R-packages
RUN Rscript ./install_packages.R

# copy everything
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
