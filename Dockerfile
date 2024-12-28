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
COPY server.py .
ENV JEOPARDY_GAME_ROOT=games/
ENV J_GAME_ROOT=games
ENV PYTHONUNBUFFERED=1
EXPOSE 10002
CMD ["python", "server.py"]
