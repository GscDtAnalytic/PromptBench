FROM node:20-alpine

WORKDIR /app

# Instala deps a partir do package.json (sem lock; uso npm em modo "primeira instalação")
COPY package.json /app/
RUN npm install --omit=optional

# Copia o resto (em dev, volume monta por cima)
COPY . /app

ENV NEXT_TELEMETRY_DISABLED=1
EXPOSE 3000
CMD ["npm", "run", "dev"]
