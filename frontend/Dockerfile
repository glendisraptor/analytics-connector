# Use Node 20 LTS base image
FROM node:20-bullseye

# Set working directory
WORKDIR /app

# Copy package.json and package-lock.json first for caching
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy rest of the frontend source code
COPY . .

# Expose port
EXPOSE 5173

# Run Vite in dev mode
CMD ["npm", "run", "dev"]
