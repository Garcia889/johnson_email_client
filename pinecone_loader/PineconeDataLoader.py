import os
import json
import time
from tqdm import tqdm
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec

class PineconeDataLoader:
    """
    Clase que carga datos desde un archivo JSON, genera embeddings para esos datos
    utilizando el modelo de OpenAI, y los inserta en un índice de Pinecone.

    Atributos:
        PINECONE_API_KEY (str): Clave API para autenticar el acceso a Pinecone.
        PINECONE_ENV (str): Entorno de Pinecone (por ejemplo, "us-west1").
        OPENAI_API_KEY (str): Clave API para autenticar el acceso a OpenAI.
        EMBEDDING_MODEL (str): Modelo de OpenAI para generar embeddings.
        BATCH_SIZE (int): Cantidad de elementos por lote a procesar.
        DATA_FILE (str): Ruta del archivo JSON con los datos a cargar.
        PINECONE_INDEX (str): Nombre del índice en Pinecone.
        pc (Pinecone): Cliente para interactuar con Pinecone.
        openai (OpenAI): Cliente para interactuar con OpenAI.
        index (PineconeIndex): Instancia del índice de Pinecone donde se cargan los datos.
    """
    def __init__(self, json_file: str, pinecone_index: str):
        # ==== Cargar variables del entorno ====
        load_dotenv(override=True)
        
        self.PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
        self.PINECONE_ENV = os.getenv("PINECONE_ENV")
        self.OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
        
        self.EMBEDDING_MODEL = "text-embedding-3-small"
        self.BATCH_SIZE = int(os.getenv("BATCH_SIZE", 100))
        self.DATA_FILE = json_file
        self.PINECONE_INDEX = pinecone_index
        
        # ==== Inicializar clientes ====
        self.pc = Pinecone(api_key=self.PINECONE_API_KEY)
        self.openai = OpenAI(api_key=self.OPENAI_API_KEY)
        self.index = None

    def ensure_index_exists(self):
        """Verifica si el índice existe y lo crea si no"""
        index_names = self.pc.list_indexes().names()
        if self.PINECONE_INDEX not in index_names:
            print(f"🛠 Creando índice '{self.PINECONE_INDEX}' en {self.PINECONE_ENV}...")
            self.pc.create_index(
                name=self.PINECONE_INDEX,
                dimension=1536,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region=self.PINECONE_ENV
                )
            )
            while not self.pc.describe_index(self.PINECONE_INDEX).status['ready']:
                print("⏳ Esperando a que el índice esté listo...")
                time.sleep(3)
        else:
            print(f"✅ Índice '{self.PINECONE_INDEX}' ya existe.")

    def load_data(self, filepath: str) -> list:
        """Carga datos desde un archivo JSON"""
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def generate_embedding(self, text: str) -> list:
        """Genera embeddings usando OpenAI"""
        try:
            response = self.openai.embeddings.create(
                input=text,
                model=self.EMBEDDING_MODEL
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"⚠️ Error generando embedding: {e}")
            return None

    def format_vector(self, item: dict) -> dict:
        """Formatea un item para ser insertado en Pinecone"""
        embedding = self.generate_embedding(item["content"])
        if embedding is None:
            return None
            
        metadata = {
            "subject": item.get("subject", ""),
            "content": item["content"],
            "sender": item.get("sender", ""),
            "timestamp": item.get("timestamp", ""),
            "category": item.get("category", ""),
            "summary": item.get("summary", ""),
            "suggested_response": item.get("suggested_response", ""),
            "thread_id": item.get("thread_id", "")
        }
        
        return {
            "id": item["id"],
            "values": embedding,
            "metadata": metadata
        }

    def upsert_batch(self, batch: list):
        """Inserta un lote de vectores en Pinecone"""
        if batch:
            self.index.upsert(vectors=batch)

    def process_data(self, items: list):
        """Procesa los datos y los carga en Pinecone por lotes"""
        batch = []
        for item in tqdm(items, desc="🔄 Subiendo a Pinecone"):
            vector = self.format_vector(item)
            if vector:
                batch.append(vector)
            if len(batch) >= self.BATCH_SIZE:
                self.upsert_batch(batch)
                batch = []
                time.sleep(1)
        if batch:
            self.upsert_batch(batch)

    def run(self):
        """Método principal que ejecuta todo el proceso"""
        self.ensure_index_exists()
        self.index = self.pc.Index(self.PINECONE_INDEX)
        
        print("📦 Cargando datos...")
        items = self.load_data(self.DATA_FILE)
        
        print(f"📨 Procesando {len(items)} items...")
        self.process_data(items)
        
        print("🎉 ¡Carga completada!")


# Ejemplo de uso
if __name__ == "__main__":
    # Crear instancia con el archivo JSON y el nombre del índice
    loader = PineconeDataLoader(
        json_file="./data/cotizaciones.json",  # Nombre del archivo JSON
        pinecone_index="banquetes-emails"  # Nombre del índice en Pinecone
    )
    
    # Ejecutar el proceso
    loader.run()