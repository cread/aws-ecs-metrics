SRC=Dockerfile aws-ecs-metrics.py

all:
.PHONY: all

build: $(SRC)
	docker build -t aws-ecs-metrics:latest .
.PHONY: build

push:	build
	docker tag aws-ecs-metrics cread/aws-ecs-metrics
	docker push cread/aws-ecs-metrics
.PHONY: push
