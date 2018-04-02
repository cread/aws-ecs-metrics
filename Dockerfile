FROM python:3.6-alpine

RUN pip install docker boto3

COPY aws-ecs-metrics.py /aws-ecs-metrics

ENTRYPOINT /aws-ecs-metrics

VOLUME /var/run/docker.sock
