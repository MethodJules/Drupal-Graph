# Get ubuntu
FROM ubuntu:18.04

# Update Package Manager
RUN apt-get update && apt-get install -y software-properties-common -y
RUN apt-get update && add-apt-repository ppa:deadsnakes/ppa -y
RUN apt-get update && apt install python3.7 -y
RUN apt-get update && apt-get install python3-pip -y
RUN pip3 --version

ENV LANG C.UTF-8

ADD . /app
RUN python3 -m pip install -U spacy
RUN python3 -m spacy download en
RUN python3 -m spacy download en_core_web_lg
RUN python3 -m pip install neo4j
RUN python3 -m pip install nltk
RUN python3 -m pip install annoy
RUN python3 -m pip install flask
RUN python3 -m pip install unidecode

# Open Port
EXPOSE 5000

# Install java
RUN apt-get update && apt-get install default-jre -y
RUN java --version

#RUN mkdir /opt/corenlp
#ADD ../corenlp /opt/corenlp
#USER nlp
#RUN chown -R nlp:nlp /opt/corenlp
#RUN chmod 755 -R /opt/corenlp

WORKDIR /app

ENTRYPOINT [ "python3" ]

CMD [ "app.py" ]




