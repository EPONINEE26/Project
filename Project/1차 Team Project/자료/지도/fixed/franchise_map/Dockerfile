FROM python:3.13-slim
WORKDIR /app
COPY index.html serve.py ./
COPY assets ./assets
ENV PORT=8080
EXPOSE 8080
CMD ["python", "serve.py", "--host", "0.0.0.0", "--no-browser"]
