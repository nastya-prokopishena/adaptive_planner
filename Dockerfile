FROM node:20.19.0 AS frontend-build

WORKDIR /frontend

COPY frontend/package*.json ./
RUN npm install

COPY frontend/ ./
RUN npm run build


FROM python:3.11

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY run.py /app/run.py
COPY backend /app/backend

RUN rm -rf /app/backend/static
COPY --from=frontend-build /frontend/dist /app/backend/static

EXPOSE 5000

CMD ["python", "run.py"]