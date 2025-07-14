FROM owasp/zap2docker-stable

LABEL maintainer="security@example.com"
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 python3-pip curl unzip git \
    && pip3 install lxml zeep

COPY entrypoint.sh /entrypoint.sh
COPY generate_tests_from_wsdl.py /zap/generate_tests_from_wsdl.py
COPY opa /zap/opa
RUN chmod +x /entrypoint.sh

WORKDIR /zap
ENTRYPOINT ["/entrypoint.sh"]