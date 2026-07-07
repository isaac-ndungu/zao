ARG NODE_ENV=development
FROM node:22-slim

WORKDIR /app

COPY package.json package-lock.json ./

RUN npm install

COPY . .

ARG VITE_GOOGLE_CLIENT_ID
ARG VITE_API_PROXY=http://localhost:8000

ENV VITE_GOOGLE_CLIENT_ID=$VITE_GOOGLE_CLIENT_ID
ENV VITE_API_PROXY=$VITE_API_PROXY

EXPOSE 5173

CMD ["npm", "run", "dev"]
