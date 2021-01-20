FROM mxnet/r-lang:latest
# This example uses mxnet, which is a huge pain to install so we use the
# mxnet base image. If you don't need mxnet, or you need a newer version of R,
# then replace the FROM statement with the following:
# FROM r-base:latest

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

# Replace this with the name of your script
CMD [ "Rscript", "./main.R" ]
