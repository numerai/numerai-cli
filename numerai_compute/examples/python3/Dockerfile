FROM python:3.7

ADD requirements.txt .
RUN pip install -r requirements.txt

ADD . .

ARG NUMERAI_PUBLIC_ID
ENV NUMERAI_PUBLIC_ID=$NUMERAI_PUBLIC_ID

ARG NUMERAI_SECRET_KEY
ENV NUMERAI_SECRET_KEY=$NUMERAI_SECRET_KEY

CMD [ "python", "./predict.py" ]
