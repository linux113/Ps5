# LEONIDA LIVE — static app image (zero build step, stdlib server)
FROM python:3.12-alpine
WORKDIR /app
COPY index.html styles.css app.js seed-flags.json ./
EXPOSE 3000
CMD ["python", "-m", "http.server", "3000", "--bind", "0.0.0.0"]
