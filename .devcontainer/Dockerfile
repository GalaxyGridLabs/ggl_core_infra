FROM mcr.microsoft.com/devcontainers/python:1-3.12-bullseye

RUN install -o vscode -g vscode -D /commandhistory && \
    install -o vscode -g vscode /dev/null /commandhistory/.bash_history && \
    SNIPPET='export PROMPT_COMMAND=\"history -a\" && export HISTFILE=/commandhistory/.bash_history' && \
    echo $SNIPPET >> '/home/vscode/.bashrc'