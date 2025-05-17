FROM node:16-alpine

WORKDIR /app
COPY static/ .

RUN npm install -g http-server

EXPOSE 8080

CMD ["http-server", "-p", "8080", "--proxy", "http://api:8000?"]