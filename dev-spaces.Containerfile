FROM registry.access.redhat.com/ubi9/python-39:latest

RUN microdnf install -y openssl compat-openssl11 libbrotli