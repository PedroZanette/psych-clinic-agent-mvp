import os
import json
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def parse_patient_message_with_gemini(message: str) -> dict:
    prompt = f"""
Você é uma assistente de clínica de psicologia.

Analise a mensagem abaixo e retorne APENAS JSON válido, sem markdown.

Campos obrigatórios:
- intent: "reschedule" ou "unknown"
- preference: "manha", "tarde", "noite" ou null
- urgency: "alta" ou "média"
- reply: resposta curta, natural e profissional para o paciente

Regra importante:
- Se a mensagem for um pedido de remarcação, a resposta deve confirmar entendimento e dizer que irá verificar opções.
- Não pergunte novas informações ao paciente, a menos que seja realmente indispensável.

Mensagem:
{message}
""".strip()

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

        text = response.text.strip()
        text = text.replace("```json", "").replace("```", "").strip()

        data = json.loads(text)

        return {
            "intent": data.get("intent", "unknown"),
            "preference": data.get("preference"),
            "urgency": data.get("urgency", "média"),
            "reply": data.get("reply", "Entendi. Vou verificar opções para você."),
            "raw_model_output": text,
            "used_gemini": True,
            "gemini_error": None,
        }

    except Exception as e:
        return {
            "intent": "unknown",
            "preference": None,
            "urgency": "média",
            "reply": "Entendi! Vou verificar opções de remarcação para você.",
            "raw_model_output": "",
            "used_gemini": False,
            "gemini_error": str(e),
        }


def generate_confirmation_with_gemini(
    patient_name: str,
    psychologist_name: str,
    old_time: str,
    new_time: str,
) -> str:
    prompt = f"""
Escreva uma mensagem curta, humana e profissional em português do Brasil para confirmar uma remarcação de consulta.

Contexto:
- Paciente: {patient_name}
- Psicóloga: {psychologist_name}
- Horário antigo: {old_time}
- Novo horário: {new_time}

Retorne apenas a mensagem final.
""".strip()

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text.strip()

    except Exception:
        return (
            f"Olá, {patient_name}! Sua consulta com {psychologist_name} foi remarcada com sucesso. "
            f"O horário anterior era {old_time} e o novo horário é {new_time}."
        )