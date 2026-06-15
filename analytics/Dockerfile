FROM node:20-bookworm

ENV PIP_BREAK_SYSTEM_PACKAGES=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip \
    && pip3 install --no-cache-dir \
        dagster==1.11.16 \
        dagster-webserver==1.11.16 \
        dbt-core==1.11.11 \
        dbt-postgres==1.10.0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

CMD ["dbt", "build", "--project-dir", ".", "--profiles-dir", ".", "--target", "investment_signals"]
