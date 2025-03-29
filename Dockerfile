FROM alpine:latest
# Install system dependencies
RUN apk add --update --no-cache python3 py3-pip py3-virtualenv
# Install python dependencies
COPY requirements.txt .
RUN python3 -m venv /opt/venv && . /opt/venv/bin/activate
RUN PATH="/opt/venv/bin:$PATH"
RUN pip install -Ur requirements.txt --break-system-packages
# Copy source code
COPY fetchardy.py .
ENV JEOPARDY_GAME_ROOT=games/
ENV J_GAME_ROOT=games
ENV PYTHONUNBUFFERED=1
CMD ["sh", "-c", "DD_SERVICE=\"fetchardy\" DD_ENV=\"develop\" DD_LOGS_INJECTION=true DD_PROFILING_ENABLED=true DD_GIT_COMMIT_SHA=\"<GIT_COMMIT_SHA>\"  DD_GIT_REPOSITORY_URL=\"<GIT_REPOSITORY_URL>\" ; ddtrace-run python fetchardy.py get-latest ; ddtrace-run python -m flask --app fetchardy run -h 0.0.0.0 -p 80"]
