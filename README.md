# Psych Clinic Agent MVP

MVP de uma **assistente virtual para clínicas de psicologia**, focada em **remarcação de consultas**, com **IA para interpretação da mensagem**, **regras configuráveis por psicóloga** e **integração real com Google Calendar**.

## Visão geral

Este projeto foi desenvolvido como uma prova de conceito para uma assistente virtual capaz de atuar como uma **atendente digital** dentro de uma clínica de psicologia.

O objetivo do MVP é validar o núcleo do problema real:

- receber uma solicitação de remarcação;
- entender a intenção do paciente;
- aplicar regras específicas da psicóloga;
- sugerir ou aprovar novos horários;
- concluir a remarcação;
- atualizar a consulta no calendário.

A proposta é que essa base evolua para uma assistente configurável por clínica e profissional, podendo futuramente operar em canais como WhatsApp e ser orquestrada por ferramentas como n8n.

---

## Problema

A remarcação de consultas em clínicas costuma envolver:

- troca manual de mensagens;
- validação com a psicóloga;
- regras diferentes por profissional;
- risco de erro no horário;
- falta de padronização no atendimento.

Além disso, em uma operação real, diferentes psicólogas podem ter comportamentos distintos, como:

- exigir ou não aprovação para remarcação;
- cobrar de formas diferentes;
- usar agendas e rotinas específicas;
- se comunicar com tons diferentes.

Esse cenário exige uma solução que vá além de um chatbot simples: é necessário um **motor de atendimento configurável**, com camada de IA e execução operacional confiável.

---

## Solução proposta

Este MVP implementa uma assistente virtual com foco em **remarcação de consultas**, combinando:

- **Gemini** para interpretação de mensagem e respostas mais naturais;
- **regras determinísticas** para controle do fluxo;
- **Google Calendar API** para validação de integração real com agenda;
- **interface em Streamlit** para simular o uso da assistente em contexto de operação.

A arquitetura foi pensada para permitir evolução futura para:

- múltiplas clínicas;
- múltiplas psicólogas;
- skills por contexto;
- integração com canais reais;
- orquestração via n8n;
- uso mais amplo de agentes.

---

## O que o MVP faz

### Fluxo 1 — paciente solicita remarcação
- paciente envia mensagem;
- a IA interpreta a intenção;
- o sistema identifica a consulta;
- aplica as regras da psicóloga;
- sugere novos horários;
- a psicóloga aprova;
- a consulta é remarcada;
- o evento pode ser atualizado no Google Calendar.

### Fluxo 2 — psicóloga inicia remarcação
- a psicóloga solicita a mudança;
- o sistema cria uma proposta;
- o paciente pode aceitar ou recusar;
- se aceitar, a consulta é remarcada;
- o evento pode ser atualizado no Google Calendar.

---

## Diferenciais do MVP

- **IA real na camada de entendimento**  
  O Gemini é usado para interpretar mensagens em linguagem natural e gerar respostas iniciais e finais mais humanas.

- **Integração real com agenda**  
  O projeto valida a atualização de eventos no Google Calendar.

- **Regras por psicóloga**  
  Cada profissional pode ter configurações próprias de agenda, política de aprovação e comportamento.

- **WhatsApp simulado**  
  O canal de atendimento foi simulado para aproximar o MVP de um cenário real, sem depender da integração completa com a API do WhatsApp nesta etapa.

- **Arquitetura evolutiva**  
  O projeto foi estruturado para permitir evolução futura para uma assistente configurável por clínica, profissional e contexto.

---

## Arquitetura lógica

O sistema foi organizado em módulos lógicos com responsabilidades separadas:

- **Orchestrator**  
  Coordena o fluxo geral da solicitação.

- **Policy Agent**  
  Aplica as regras da psicóloga/clínica.

- **Scheduling Agent**  
  Sugere horários compatíveis com a agenda.

- **Communication Agent**  
  Gera respostas e confirmações para paciente e psicóloga.

- **Google Calendar Adapter**  
  Faz o vínculo e a atualização de eventos reais no Google Calendar.

> Nesta fase, os “agentes” foram modelados como módulos lógicos em Python. A orquestração futura pode ser expandida para frameworks de agentes e/ou n8n.

---

## Tecnologias utilizadas

- **Python**
- **Streamlit**
- **Google Calendar API**
- **Gemini API**
- **dotenv**
- **OAuth 2.0**

---

## Estrutura do projeto

```bash
psych-clinic-agent-mvp/
├── app.py
├── gemini_service.py
├── google_calendar_service.py
├── test_gemini.py
├── run_local.bat
├── requirements.txt
├── README.md
├── .env.example
├── testes/
│   └── test_calendar.py
├── credentials.json        
├── token.json              
└── .env                    