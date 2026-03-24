# Psych Clinic Agent MVP

## Objetivo
Protótipo de assistente virtual para remarcação de consultas em clínicas de psicologia, com regras configuráveis por psicóloga e integração com Google Calendar.

## O que o MVP faz
- paciente solicita remarcação
- sistema identifica intenção
- aplica regras da psicóloga
- sugere novos horários
- psicóloga aprova
- consulta é remarcada
- evento é atualizado no Google Calendar

## Arquitetura
- Orchestrator
- Policy Agent
- Scheduling Agent
- Communication Agent
- Google Calendar Adapter

## Tecnologias
- Python
- Streamlit
- Google Calendar API

## Próximos passos
- integrar freeBusy para disponibilidade real
- plugar n8n como orquestrador
- adicionar LLM para entendimento mais natural
- transformar regras em skills por clínica/profissional
- integrar canais como WhatsApp