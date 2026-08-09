FROM eclipse-temurin:21-jdk-alpine

RUN adduser -D -u 1000 sandbox
USER sandbox

WORKDIR /sandbox

