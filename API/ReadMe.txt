Usamos Fast API

--Para hacer pruebas del API usamos PostMan
https://www.postman.com/downloads

--Este comando inicia el servicio de Fast API
uvicorn main:app –-reload

Para correlo usamos un ambiente virtual de conda
--Actualizamos Conda
Conda update conda

--Creamos el ambiente virtual
conda create --name cred_env

--Activamos ambiente virtual
conda activate cred_env

--Agregamos Conda forge para encontrar el paquete de Fast API
conda config --add channels conda-forge

--Instalamos paquete de Fast API
conda install “fastapi”

--Instalamos servidor de Fast API
conda install "uvicorn[standard]"
