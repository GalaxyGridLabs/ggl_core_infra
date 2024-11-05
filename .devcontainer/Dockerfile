FROM mcr.microsoft.com/devcontainers/python:1-3.12-bullseye

RUN install -o vscode -g vscode -d /commandhistory && \
    install -o vscode -g vscode /dev/null /commandhistory/.bash_history && \
    echo "export PROMPT_COMMAND='history -a' && export HISTFILE=/commandhistory/.bash_history" >> "/home/vscode/.bashrc" && \
    echo "export PYTHONPATH=/workspaces/ggl_core_infra/src/" >> "/home/vscode/.bashrc"

USER vscode