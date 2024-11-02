FROM mcr.microsoft.com/devcontainers/python:3.12
RUN apt update && apt install -y curl git apt-transport-https ca-certificates gnupg
RUN curl -fsSL https://get.pulumi.com | sh

# Install gcloud CLI
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list && \
    curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg && \
    apt-get update -y && \
    apt-get install google-cloud-sdk -y