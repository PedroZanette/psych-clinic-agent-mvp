from gemini_service import parse_patient_message_with_gemini

msg = "Oi, queria remarcar minha consulta. Pode ser de tarde?"
print(parse_patient_message_with_gemini(msg))

