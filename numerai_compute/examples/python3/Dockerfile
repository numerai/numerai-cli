FROM python:3

ADD requirements.txt .
RUN pip install -r requirements.txt

ADD . .

ARG NUMERAI_PUBLIC_ID
RUN test -n "$NUMERAI_PUBLIC_ID" || (echo "Error: you need to set the NUMERAI_PUBLIC_ID build arg" && exit 1)
ENV NUMERAI_PUBLIC_ID=$NUMERAI_PUBLIC_ID

ARG NUMERAI_SECRET_KEY
RUN test -n "$NUMERAI_SECRET_KEY" || (echo "Error: you need to set the NUMERAI_SECRET_KEY build arg" && exit 1)
ENV NUMERAI_SECRET_KEY=$NUMERAI_SECRET_KEY

CMD [ "python", "./predict.py" ]
