# Usamos imagen de Python
FROM python:3.9-slim-buster

RUN apt-get update \
    && apt-get -y install libpq-dev gcc \
    && pip install psycopg2
# Establecemos el directorio de trabajo del contenedor
WORKDIR /app

# Copiamos el contenido del directorio actual a /app
COPY . /app


# Create a virtual environment
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"

# Copy the requirements.txt file and install Python dependencies
COPY requirements.txt /
#RUN pip install --no-cache-dir -r /requirements.txt

# Instalamos paquetes especificados en requirements.txt
#COPY ./requirements.txt .

RUN pip3 install -r requirements.txt

#RUN pip install --no-cache-dir -r requirements.txt

# Exponemos puerto 8000
EXPOSE 8000

# Define environment variable
# ENV NAME World

# Iniciamos servicio de Fast API
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
