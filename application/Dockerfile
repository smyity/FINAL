FROM python:3.11-slim

WORKDIR /app

ENV GOPATH=/go
ENV GOCACHE=/root/.cache/go-build

# установка необходимых приложений
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        supervisor \
        golang-go \
        wget \
        ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# инициализация окружения для Go (для компиляции кода в .exe файл)
RUN go mod init win_monitor && \
    go get github.com/shirou/gopsutil/v3 && \
    go mod tidy

# установка зависимостей для работы приложения на Linux сервере
RUN pip install --no-cache-dir fastapi uvicorn pydantic streamlit requests clickhouse-connect pandas

# копирование файлов приложения для работы контейнера
COPY back.py front.py supervisord.conf ./

EXPOSE 1111 1112
# 1111 - бэкенд
# 1112 - фронтенд

# запуск supervisor для управления FastAPI и Streamlit в одном контейнере
CMD ["/usr/bin/supervisord", "-c", "/app/supervisord.conf"]
