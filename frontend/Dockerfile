FROM artprod.dev.bloomberg.com/node:20-rhel8

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .

EXPOSE 3000
CMD ["npm", "run", "dev"]
