FROM python:3.7

ADD requirements.txt .
RUN pip install -r requirements.txt

ADD . .

# NUMERAI_PUBLIC_ID and NUMERAI_SECRET_KEY actually aren't used. These lines
# just prevent a warning about unused args being passed into `docker build`
ARG NUMERAI_PUBLIC_ID
ARG NUMERAI_SECRET_KEY

ADD .numerai-api-keys /.numerai-api-keys
CMD [ "bash", "-c", "source /.numerai-api-keys && python ./predict.py" ]
