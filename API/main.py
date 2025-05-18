from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any
import os
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone
import statistics

app = FastAPI()

# Configura CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, reemplaza "*" con tu dominio frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelo para la solicitud
class EmailRequest(BaseModel):
    sender: str
    subject: str
    content: str

# Modelo para la respuesta
class EmailResponse(BaseModel):
    input: Dict[str, Any]
    classification: Dict[str, Any]
    response: Dict[str, Any]
    metadata: Dict[str, Any]

class EmailAssistant:
    def __init__(self, pinecone_index_name: str):
        load_dotenv(override=True)
        
        self.PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
        self.OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
        self.EMBEDDING_MODEL = "text-embedding-3-small"
        self.TOP_K = 5
        self.CONFIDENCE_THRESHOLD = 0.65
        
        self.pc = Pinecone(api_key=self.PINECONE_API_KEY)
        self.openai = OpenAI(api_key=self.OPENAI_API_KEY)
        self.index = self.pc.Index(pinecone_index_name)
    
    def generate_embedding(self, text: str) -> list:
        try:
            response = self.openai.embeddings.create(
                input=text,
                model=self.EMBEDDING_MODEL
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Error generando embedding: {e}")
            return None
    
    def query_similar_emails(self, sender: str, subject: str, content: str) -> list:
        try:
            combined_text = f"From: {sender}\nSubject: {subject}\n\n{content}"
            embedding = self.generate_embedding(combined_text)
            
            if not embedding:
                return []
            
            results = self.index.query(
                vector=embedding,
                top_k=self.TOP_K,
                include_metadata=True
            )
            return results.matches
        except Exception as e:
            print(f"Error consultando Pinecone: {e}")
            return []
    
    def analyze_results(self, similar_emails: list) -> Dict[str, Any]:
        if not similar_emails:
            return {}
        
        categories = {}
        suggested_responses = []
        scores = []
        
        for email in similar_emails:
            metadata = email.metadata
            score = email.score
            scores.append(score)
            
            category = metadata.get('category', 'Desconocida')
            if category not in categories:
                categories[category] = 0
            categories[category] += score
            
            if 'suggested_response' in metadata and metadata['suggested_response']:
                suggested_responses.append(metadata['suggested_response'])
        
        avg_score = statistics.mean(scores) if scores else 0
        max_score = max(scores) if scores else 0
        
        total = sum(categories.values())
        normalized_categories = {k: v/total for k, v in categories.items()}
        
        main_category = max(normalized_categories.items(), key=lambda x: x[1]) if normalized_categories else ('Desconocida', 0)
        
        return {
            'categories': normalized_categories,
            'main_category': main_category[0],
            'confidence': main_category[1],
            'suggested_responses': suggested_responses,
            'average_similarity': avg_score,
            'max_similarity': max_score,
            'total_matches': len(similar_emails)
        }
    
    def generate_ai_response(self, responses: list, sender: str, subject, content) -> str:
        '''This function generates a response using OpenAI's API, sends
        the responses to the model, and returns the generated response.'''
        if not responses:
            return "No tengo una respuesta sugerida para este correo."
        try:
            prompt = f"Responde al siguiente correo:\n\nDe: {sender}\nAsunto: {subject}\n\n{content}\n\nRespuestas sugeridas:\n"
            for i, response in enumerate(responses):
                prompt += f"{i + 1}. {response}\n"
            prompt += "\nPersonaliza la respuesta con un estilo parecido a los ejemplos pero con formato adecuado para e-mail, quita asteriscos y símbolos innecesarios\n"

            response = self.openai.chat.completions.create(
                model="gpt-4-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=850,
                n=1,
                stop=None
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error generando respuesta AI: {e}")
            return self.generate_response(responses, sender)  

    def generate_response(self, responses: list, sender: str) -> str:
        if not responses:
            return "No tengo una respuesta sugerida para este correo."
        
        if len(responses) > 3:
            response_counts = {}
            for r in responses:
                if r not in response_counts:
                    response_counts[r] = 0
                response_counts[r] += 1
            
            most_common = max(response_counts.items(), key=lambda x: x[1])
            base_response = most_common[0]
        else:
            base_response = responses[0]
        
        personalized_response = base_response
        if sender and any(word in sender.lower() for word in ['@', '.com', '.mx']):
            name_part = sender.split('@')[0]
            if '.' in name_part:
                name = name_part.split('.')[0].title()
                personalized_response = personalized_response.replace("[Nombre]", name)
        
        return personalized_response
    
    def process_email(self, sender: str, subject: str, content: str) -> Dict[str, Any]:
        similar_emails = self.query_similar_emails(sender, subject, content)
        analysis = self.analyze_results(similar_emails)
        
        # Genera un resumen del contenido usando OpenAI
        try:
            summary_prompt = f"Resume brevemente el siguiente correo \n\n{content}\n\n Regresa respuesta en español"
            summary_response = self.openai.chat.completions.create(
                model="gpt-4-turbo",
                messages=[{"role": "user", "content": summary_prompt}],
                max_tokens=120,
                n=1,
                stop=None
            )
            summary = summary_response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error generando resumen: {e}")
            summary = ""

        analysis['summary'] = summary
        
        if not analysis:
            return {
                'error': 'No se encontraron correos similares en la base de datos',
                'input': {'sender': sender, 'subject': subject}
            }
        
        suggested_response = self.generate_ai_response(
            analysis.get('suggested_responses', []),
            sender,
            subject,
            content
        )
        
        return {
            'input': {
                'sender': sender,
                'subject': subject,
                'content_preview': content[:100] + '...' if len(content) > 100 else content
            },
            'classification': {
                'main_category': analysis['main_category'],
                'confidence': analysis['confidence'],
                'is_confident': analysis['confidence'] >= self.CONFIDENCE_THRESHOLD,
                'all_categories': analysis['categories'],
                'summary': analysis['summary']
            },
            'response': {
                'suggested': suggested_response,
                'based_on_n_examples': len(analysis['suggested_responses']),
                'average_similarity': analysis['average_similarity']
            },
            'metadata': {
                'total_matches': analysis['total_matches'],
                'model_used': self.EMBEDDING_MODEL
            }
        }

# Inicializar el asistente (ajusta el nombre del índice)
assistant = EmailAssistant("banquetes-emails")

@app.post("/process-email", response_model=EmailResponse)
async def process_email(email: EmailRequest):
    try:
        result = assistant.process_email(
            sender=email.sender,
            subject=email.subject,
            content=email.content
        )
        
        if 'error' in result:
            raise HTTPException(status_code=404, detail=result['error'])
            
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "Email Assistant API - Envía un correo a /process-email"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)