import requests
from django.conf import settings

def mensaje_prueba(telefono_paciente, nombre_paciente, fecha_cita):
    url = f"https://graph.facebook.com/v18.0/{settings.WHATSAPP_PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
        "Content/Type": "application/json"
    }

    payload = {
            "messaging_product": "whatsapp",
            "to": telefono_paciente,
            "type": "template",
            "template": {
                "name": "pacientes.html",
                "language": {
                    "code": "es"
                },
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": nombre_paciente},
                            {"type": "text", "text": str(fecha_cita)}
                        ]
                    }
                ]
            }
        }
    response = requests.post(url, headers=headers, json=payload)
    return response.json()