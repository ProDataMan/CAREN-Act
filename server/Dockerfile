# Build context is the repository root (the image also serves website/ and docs/).
FROM node:22-alpine
WORKDIR /app
COPY server/package.json server/package-lock.json ./server/
RUN cd server && npm ci --omit=dev && npm cache clean --force
COPY server/src ./server/src
COPY website ./website
COPY docs ./docs
ENV NODE_ENV=production PORT=8080 SITE_ROOT=/app
EXPOSE 8080
USER node
CMD ["node", "server/src/index.js"]
