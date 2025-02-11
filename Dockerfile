FROM python:3.9
WORKDIR /app
COPY . /app/
RUN pip install -r /app/requirements.txt

ENTRYPOINT ["python3","manager.py"]