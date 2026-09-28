# Runs the Vite dev server: its /api proxy forwards to the backend container (no CORS, no nginx).
FROM node:lts-slim

WORKDIR /app

# Dependencies first, so this layer is cached until package*.json changes.
COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
