import pandas as pd
import streamlit as st
from datetime import datetime, timedelta, time
from uuid import uuid4

from google_calendar_service import find_event_by_text, update_event_time, get_event_by_id

USE_GEMINI = True

try:
    from gemini_service import (
        parse_patient_message_with_gemini,
        generate_confirmation_with_gemini,
    )
    GEMINI_AVAILABLE = True
    GEMINI_IMPORT_ERROR = None
except Exception as e:
    GEMINI_AVAILABLE = False
    GEMINI_IMPORT_ERROR = str(e)

# =============================
# Integração Google Calendar
# =============================
USE_GOOGLE_CALENDAR = True
DEFAULT_GOOGLE_CALENDAR_ID = "primary"

try:
    from google_calendar_service import find_event_by_text, update_event_time
    GOOGLE_CALENDAR_AVAILABLE = True
    GOOGLE_CALENDAR_IMPORT_ERROR = None
except Exception as e:
    GOOGLE_CALENDAR_AVAILABLE = False
    GOOGLE_CALENDAR_IMPORT_ERROR = str(e)


st.set_page_config(page_title="MVP Remarcação com IA", layout="wide")

# =============================
# Dados/configurações mockadas
# =============================
PSYCHOLOGISTS = {
    "ana": {
        "id": "ana",
        "nome": "Dra. Ana",
        "calendar_id": "primary",
        "duracao_min": 50,
        "requer_aprovacao_remarcacao": True,
        "dias_permitidos": [0, 1, 2, 3],  # seg-qui
        "janelas": [(time(9, 0), time(12, 0)), (time(14, 0), time(18, 0))],
        "politica_cobranca": {
            "tipo": "pix",
            "quando": "sempre_na_terca"
        },
        "tom": "acolhedor e profissional"
    },
    "bia": {
        "id": "bia",
        "nome": "Dra. Bia",
        "calendar_id": "primary",
        "duracao_min": 50,
        "requer_aprovacao_remarcacao": False,
        "dias_permitidos": [1, 3, 4],  # ter, qui, sex
        "janelas": [(time(10, 0), time(13, 0)), (time(15, 0), time(19, 0))],
        "politica_cobranca": {
            "tipo": "mensal",
            "quando": "todo_dia_05"
        },
        "tom": "objetivo e gentil"
    }
}

PATIENTS = {
    "marina": {"id": "marina", "nome": "Marina", "telefone": "(48) 99999-1111"},
    "joao": {"id": "joao", "nome": "João", "telefone": "(48) 99999-2222"},
}


def dt(day_offset: int, hour: int, minute: int = 0):
    base = datetime.now().replace(second=0, microsecond=0)
    return (base + timedelta(days=day_offset)).replace(hour=hour, minute=minute)


def seed_consultations():
    return [
        {
            "id": "evt-1",
            "psicologa_id": "ana",
            "paciente_id": "marina",
            "paciente_nome": "Marina",
            "titulo": "Sessão - Marina / Dra. Ana",
            "inicio": dt(1, 10, 0),
            "fim": dt(1, 10, 50),
            "status": "agendada",
            "meet_link": "https://meet.google.com/demo-ana-marina",
            "observacoes": "Paciente prefere manhã",
            "calendar_id": "primary",
            "google_search_text": "TESTE MV",
            "google_event_id": None,
            "google_sync_status": "vinculado",
            "last_sync_message": "Evento previamente vinculado ao Google Calendar."
        },
        {
            "id": "evt-2",
            "psicologa_id": "ana",
            "paciente_id": "joao",
            "paciente_nome": "João",
            "titulo": "Sessão - João / Dra. Ana",
            "inicio": dt(2, 15, 0),
            "fim": dt(2, 15, 50),
            "status": "agendada",
            "meet_link": "https://meet.google.com/demo-ana-joao",
            "observacoes": "Paciente prefere tarde",
            "calendar_id": "primary",
            "google_search_text": None,
            "google_event_id": None,
            "google_sync_status": "mock",
            "last_sync_message": "Evento ainda não vinculado ao Google."
        },
        {
            "id": "evt-3",
            "psicologa_id": "bia",
            "paciente_id": "marina",
            "paciente_nome": "Marina",
            "titulo": "Sessão - Marina / Dra. Bia",
            "inicio": dt(3, 16, 0),
            "fim": dt(3, 16, 50),
            "status": "agendada",
            "meet_link": "https://meet.google.com/demo-bia-marina",
            "observacoes": "Paciente topa noite",
            "calendar_id": "primary",
            "google_search_text": None,
            "google_event_id": None,
            "google_sync_status": "mock",
            "last_sync_message": "Evento ainda não vinculado ao Google."
        }
    ]

def reset_demo_state():
    st.session_state.consultations = seed_consultations()
    st.session_state.requests = []
    st.session_state.chat_history = []

# =============================
# Estado da aplicação
# =============================
if "consultations" not in st.session_state:
    st.session_state.consultations = seed_consultations()

if "requests" not in st.session_state:
    st.session_state.requests = []

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


def sync_consultation_from_google(consultation: dict):
    if not USE_GOOGLE_CALENDAR or not GOOGLE_CALENDAR_AVAILABLE:
        return

    calendar_id = consultation.get("calendar_id", "primary")
    event_id = consultation.get("google_event_id")

    if not event_id:
        return

    try:
        event = get_event_by_id(calendar_id, event_id)

        start_raw = event.get("start", {}).get("dateTime")
        end_raw = event.get("end", {}).get("dateTime")

        if start_raw and end_raw:
            consultation["inicio"] = datetime.fromisoformat(start_raw.replace("Z", "+00:00")).replace(tzinfo=None)
            consultation["fim"] = datetime.fromisoformat(end_raw.replace("Z", "+00:00")).replace(tzinfo=None)

        consultation["last_sync_message"] = "Consulta sincronizada com horário real do Google Calendar."
        consultation["google_sync_status"] = "sincronizado"

        if event.get("hangoutLink"):
            consultation["meet_link"] = event["hangoutLink"]

    except Exception as e:
        consultation["last_sync_message"] = f"Falha ao sincronizar horário do Google: {e}"
        consultation["google_sync_status"] = "erro"

# =============================
# Helpers Google
# =============================
def resolve_google_event_for_consultation(consultation: dict):
    if not USE_GOOGLE_CALENDAR:
        return None, "Integração com Google Calendar desativada."

    if not GOOGLE_CALENDAR_AVAILABLE:
        return None, f"Serviço do Google indisponível: {GOOGLE_CALENDAR_IMPORT_ERROR}"

    if consultation.get("google_event_id"):
        return consultation["google_event_id"], "Evento já vinculado."

    search_text = consultation.get("google_search_text") or consultation.get("titulo")
    calendar_id = consultation.get("calendar_id", DEFAULT_GOOGLE_CALENDAR_ID)

    if not search_text:
        return None, "Consulta sem texto de busca para localizar evento no Google."

    try:
        event = find_event_by_text(calendar_id, search_text)
        if not event:
            consultation["google_sync_status"] = "nao_encontrado"
            consultation["last_sync_message"] = f"Nenhum evento encontrado para '{search_text}'."
            return None, consultation["last_sync_message"]

        consultation["google_event_id"] = event["id"]
        start_raw = event.get("start", {}).get("dateTime")
        end_raw = event.get("end", {}).get("dateTime")

        if start_raw and end_raw:
            consultation["inicio"] = datetime.fromisoformat(start_raw.replace("Z", "+00:00")).replace(tzinfo=None)
            consultation["fim"] = datetime.fromisoformat(end_raw.replace("Z", "+00:00")).replace(tzinfo=None)

        if event.get("hangoutLink"):
            consultation["meet_link"] = event["hangoutLink"]
        consultation["google_sync_status"] = "vinculado"
        consultation["last_sync_message"] = f"Evento vinculado com sucesso: {event.get('summary', '(sem título)')}"

        if event.get("hangoutLink"):
            consultation["meet_link"] = event["hangoutLink"]

        return consultation["google_event_id"], consultation["last_sync_message"]

    except Exception as e:
        consultation["google_sync_status"] = "erro"
        consultation["last_sync_message"] = f"Erro ao buscar evento no Google: {e}"
        return None, consultation["last_sync_message"]


def maybe_sync_to_google_calendar(consultation: dict, new_start: datetime, new_end: datetime):
    result = {
        "used_google": False,
        "success": False,
        "message": "Atualização apenas local/mock."
    }

    if not USE_GOOGLE_CALENDAR:
        return result

    event_id, link_message = resolve_google_event_for_consultation(consultation)
    if not event_id:
        result["used_google"] = True
        result["message"] = link_message
        return result

    try:
        updated_event = update_event_time(
            calendar_id=consultation.get("calendar_id", DEFAULT_GOOGLE_CALENDAR_ID),
            event_id=event_id,
            new_start_iso=new_start.isoformat(),
            new_end_iso=new_end.isoformat(),
        )

        consultation["google_sync_status"] = "sincronizado"
        consultation["last_sync_message"] = "Evento atualizado no Google Calendar com sucesso."
        if updated_event.get("hangoutLink"):
            consultation["meet_link"] = updated_event["hangoutLink"]

        result["used_google"] = True
        result["success"] = True
        result["message"] = consultation["last_sync_message"]
        return result

    except Exception as e:
        consultation["google_sync_status"] = "erro"
        consultation["last_sync_message"] = f"Falha ao atualizar evento no Google Calendar: {e}"
        result["used_google"] = True
        result["message"] = consultation["last_sync_message"]
        return result


# =============================
# Funções de negócio / "agentes"
# =============================
import unicodedata

def normalize_text(text: str) -> str:
    text = text.lower().strip()
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )

def parse_patient_intent(message: str):
    msg = normalize_text(message)

    wants_reschedule = any(
        k in msg for k in ["remarcar", "remarca", "reagendar", "mudar", "outro horario"]
    )

    preference = None
    if "manha" in msg:
        preference = "manha"
    elif "tarde" in msg:
        preference = "tarde"
    elif "noite" in msg:
        preference = "noite"

    urgency = "alta" if any(k in msg for k in ["urgente", "hoje", "amanha"]) else "média"

    return {
        "intent": "reschedule" if wants_reschedule else "unknown",
        "preference": preference,
        "urgency": urgency,
        "raw": message,
    }


def find_upcoming_consultation(psicologa_id: str, paciente_id: str):
    future_items = [
        c for c in st.session_state.consultations
        if c["psicologa_id"] == psicologa_id
        and c["paciente_id"] == paciente_id
        and c["status"] == "agendada"
        and c["inicio"] > datetime.now()
    ]
    future_items.sort(key=lambda x: x["inicio"])
    return future_items[0] if future_items else None


def get_busy_slots(psicologa_id: str):
    return [
        (c["inicio"], c["fim"]) for c in st.session_state.consultations
        if c["psicologa_id"] == psicologa_id and c["status"] == "agendada"
    ]


def slot_overlaps(candidate_start: datetime, candidate_end: datetime, busy_slots):
    for b_start, b_end in busy_slots:
        if candidate_start < b_end and candidate_end > b_start:
            return True
    return False


def preference_matches(candidate_start: datetime, preference: str | None):
    if preference is None:
        return True

    hour = candidate_start.hour
    if preference == "manha":
        return 6 <= hour < 12
    if preference == "tarde":
        return 12 <= hour < 18
    if preference == "noite":
        return 18 <= hour < 22

    return True


def suggest_slots(
    psicologa_id: str,
    preference: str | None = None,
    start_date=None,
    min_datetime: datetime | None = None,
    days_ahead: int = 14,
    limit: int = 3
):
    psy = PSYCHOLOGISTS[psicologa_id]
    duration = timedelta(minutes=psy["duracao_min"])
    busy_slots = get_busy_slots(psicologa_id)
    suggestions = []

    if start_date is None:
        base_date = datetime.now().date()
    else:
        base_date = start_date

    start_day = datetime.combine(base_date, time(0, 0))

    for day in range(0, days_ahead + 1):
        current_day = start_day + timedelta(days=day)

        if current_day.weekday() not in psy["dias_permitidos"]:
            continue

        for win_start, win_end in psy["janelas"]:
            current = current_day.replace(hour=win_start.hour, minute=win_start.minute)
            end_boundary = current_day.replace(hour=win_end.hour, minute=win_end.minute)

            while current + duration <= end_boundary:
                candidate_end = current + duration

                if min_datetime and current < min_datetime:
                    current += duration
                    continue

                if (
                    not slot_overlaps(current, candidate_end, busy_slots)
                    and preference_matches(current, preference)
                ):
                    suggestions.append((current, candidate_end))
                    if len(suggestions) >= limit:
                        return suggestions

                current += duration

    return suggestions


def communication_text(role: str, psy_name: str, patient_name: str, old_time: datetime, new_time: datetime | None = None):
    if role == "patient_confirmation":
        return (
            f"Olá, {patient_name}! Sua solicitação de remarcação com {psy_name} foi registrada. "
            f"A consulta anterior era {old_time.strftime('%d/%m às %H:%M')}. "
            + (
                f"Novo horário confirmado: {new_time.strftime('%d/%m às %H:%M')}."
                if new_time
                else "Aguardando confirmação da psicóloga."
            )
        )

    if role == "psychologist_approval_request":
        return (
            f"{psy_name}, o paciente {patient_name} solicitou remarcar a consulta de "
            f"{old_time.strftime('%d/%m às %H:%M')}. Há sugestões de novos horários prontas para aprovação."
        )

    if role == "psychologist_to_patient":
        return (
            f"Olá, {patient_name}! Houve uma necessidade de ajuste na agenda de {psy_name}. "
            f"Estamos propondo novo horário para substituir a consulta de {old_time.strftime('%d/%m às %H:%M')}"
            + (f": {new_time.strftime('%d/%m às %H:%M')}." if new_time else ".")
        )

    return "Mensagem não definida."


def create_reschedule_request(
    origin: str,
    psicologa_id: str,
    paciente_id: str,
    consultation_id: str,
    preference: str | None,
    raw_message: str,
    suggestions=None,
    start_date=None,
    days_ahead: int = 14
):
    consultation = next(c for c in st.session_state.consultations if c["id"] == consultation_id)

    if suggestions is None:
        suggestions = suggest_slots(
        psicologa_id,
        preference=preference,
        start_date=consultation["inicio"].date(),
        min_datetime=consultation["inicio"],
        days_ahead=days_ahead,
        limit=3
    )

    req = {
        "id": str(uuid4()),
        "origin": origin,
        "psicologa_id": psicologa_id,
        "paciente_id": paciente_id,
        "consultation_id": consultation_id,
        "status": (
            "aguardando_aprovacao"
            if PSYCHOLOGISTS[psicologa_id]["requer_aprovacao_remarcacao"]
            else "aguardando_escolha_slot"
        ),
        "raw_message": raw_message,
        "preference": preference,
        "old_start": consultation["inicio"],
        "old_end": consultation["fim"],
        "suggestions": suggestions,
        "selected_slot": None,
        "created_at": datetime.now(),
    }

    st.session_state.requests.append(req)
    return req


def apply_reschedule(consultation_id: str, new_start: datetime, new_end: datetime):
    for c in st.session_state.consultations:
        if c["id"] == consultation_id:
            sync_info = maybe_sync_to_google_calendar(c, new_start, new_end)

            c["inicio"] = new_start
            c["fim"] = new_end

            return c, sync_info

    return None, {"used_google": False, "success": False, "message": "Consulta não encontrada."}


def summarize_request(req):
    psy_name = PSYCHOLOGISTS[req["psicologa_id"]]["nome"]
    patient_name = PATIENTS[req["paciente_id"]]["nome"]

    return {
        "solicitante": "Paciente" if req["origin"] == "patient" else "Psicóloga",
        "psicologa": psy_name,
        "paciente": patient_name,
        "preferencia": req.get("preference"),
        "consulta_original": req["old_start"].strftime("%d/%m %H:%M"),
        "status": req["status"],
        "msg": req["raw_message"]
    }

def build_requests_export_dataframe():
    rows = []

    for r in st.session_state.requests:
        consultation = next(
            (c for c in st.session_state.consultations if c["id"] == r["consultation_id"]),
            None
        )

        old_start = r["old_start"].strftime("%d/%m/%Y %H:%M") if r.get("old_start") else ""
        old_end = r["old_end"].strftime("%d/%m/%Y %H:%M") if r.get("old_end") else ""

        if r.get("selected_slot"):
            new_start = r["selected_slot"][0].strftime("%d/%m/%Y %H:%M")
            new_end = r["selected_slot"][1].strftime("%d/%m/%Y %H:%M")
        else:
            new_start = ""
            new_end = ""

        rows.append({
            "id_solicitacao": r["id"],
            "origem": "paciente" if r["origin"] == "patient" else "psicologa",
            "psicologa": PSYCHOLOGISTS[r["psicologa_id"]]["nome"],
            "paciente": PATIENTS[r["paciente_id"]]["nome"],
            "status": r["status"],
            "mensagem_original": r["raw_message"],
            "consulta_inicio_original": old_start,
            "consulta_fim_original": old_end,
            "novo_inicio": new_start,
            "novo_fim": new_end,
            "consulta_id_local": r["consultation_id"],
            "google_event_id": consultation.get("google_event_id") if consultation else None,
            "google_sync_status": consultation.get("google_sync_status") if consultation else None,
            "last_sync_message": consultation.get("last_sync_message") if consultation else None,
            "criado_em": r["created_at"].strftime("%d/%m/%Y %H:%M") if r.get("created_at") else "",
        })

    return pd.DataFrame(rows)

def get_pending_patient_proposals(psicologa_id: str, paciente_id: str):
    proposals = [
        r for r in st.session_state.requests
        if r["origin"] == "psychologist"
        and r["status"] == "proposta_ao_paciente"
        and r["psicologa_id"] == psicologa_id
        and r["paciente_id"] == paciente_id
    ]
    proposals.sort(key=lambda x: x["created_at"], reverse=True)
    return proposals

# =============================
# Cabeçalho
# =============================
st.title("MVP — Assistente de Remarcação de Consultas")
st.caption("Protótipo configurável por psicóloga, com lógica de aprovação, sugestão de horários e atualização de consulta.")

with st.expander("Arquitetura pensada para a demo"):
    st.markdown(
        """
- **Orchestrator**: recebe a solicitação e coordena o fluxo.
- **Policy Agent**: lê as regras da psicóloga/clínica.
- **Scheduling Agent**: sugere horários livres.
- **Communication Agent**: gera mensagens para paciente/psicóloga.
- **Google Calendar Adapter**: vincula e atualiza eventos reais quando disponível.

Nesta versão, os agentes são módulos lógicos em Python. O próximo passo natural é plugar n8n como orquestrador externo.
        """
    )

if USE_GOOGLE_CALENDAR:
    if GOOGLE_CALENDAR_AVAILABLE:
        st.success("Integração com Google Calendar habilitada.")
    else:
        st.warning(f"Google Calendar não disponível no momento: {GOOGLE_CALENDAR_IMPORT_ERROR}")

patient_tab, psychologist_tab, config_tab, admin_tab = st.tabs([
    "Paciente",
    "Psicóloga",
    "Configuração",
    "Admin / Estado"
])

# =============================
# Aba Paciente
# =============================
with patient_tab:
    st.subheader("Solicitação iniciada pelo paciente")
    col1, col2 = st.columns(2)

    with col1:
        paciente_id = st.selectbox(
            "Paciente",
            options=list(PATIENTS.keys()),
            format_func=lambda x: PATIENTS[x]["nome"]
        )
        psicologa_id = st.selectbox(
            "Psicóloga",
            options=list(PSYCHOLOGISTS.keys()),
            format_func=lambda x: PSYCHOLOGISTS[x]["nome"]
        )
        default_msg = "Oi, queria remarcar minha consulta. Pode ser de tarde?"
        patient_message = st.text_area("Mensagem do paciente", value=default_msg, height=120)

        if st.button("Processar solicitação do paciente", use_container_width=True):
            if USE_GEMINI and GEMINI_AVAILABLE:
                gemini_result = parse_patient_message_with_gemini(patient_message)

                if gemini_result["used_gemini"]:
                    parsed = {
                        "intent": gemini_result["intent"],
                        "preference": gemini_result["preference"],
                        "urgency": gemini_result["urgency"],
                        "raw": patient_message,
                    }
                    assistant_first_reply = gemini_result["reply"]
                else:
                    parsed = parse_patient_intent(patient_message)
                    assistant_first_reply = "Entendi! Vou verificar opções de remarcação para você."
                    st.warning("Gemini indisponível no momento. Usando fallback local.")
            else:
                parsed = parse_patient_intent(patient_message)
                assistant_first_reply = "Entendi! Vou verificar opções de remarcação para você."
            
            st.caption(f"Preferência detectada: {parsed['preference']}")
            consultation = find_upcoming_consultation(psicologa_id, paciente_id)
            if consultation:
                sync_consultation_from_google(consultation)

            if parsed["intent"] != "reschedule":
                st.warning("A mensagem não foi reconhecida como pedido de remarcação.")
            elif not consultation:
                st.error("Não encontrei consulta futura para esse paciente com essa psicóloga.")
            else:
                req = create_reschedule_request(
                    origin="patient",
                    psicologa_id=psicologa_id,
                    paciente_id=paciente_id,
                    consultation_id=consultation["id"],
                    preference=parsed["preference"],
                    raw_message=patient_message
                )
                psy = PSYCHOLOGISTS[psicologa_id]
                patient_name = PATIENTS[paciente_id]["nome"]

                st.success("Solicitação registrada.")
                st.info(f"WhatsApp (simulado) • Assistente: {assistant_first_reply}")

                if psy["requer_aprovacao_remarcacao"]:
                    st.info(
                        communication_text(
                            "psychologist_approval_request",
                            psy["nome"],
                            patient_name,
                            req["old_start"],
                            None
                        )
                    )   
                else:
                    st.info("A política desta psicóloga não exige aprovação prévia. O próximo passo é escolher um slot.")
            
    with col2:
        st.markdown("### Próxima consulta encontrada")
        consultation = find_upcoming_consultation(psicologa_id, paciente_id)

        if consultation:
            st.json({
                "paciente": consultation["paciente_nome"],
                "psicóloga": PSYCHOLOGISTS[consultation["psicologa_id"]]["nome"],
                "início": consultation["inicio"].strftime("%d/%m/%Y %H:%M"),
                "fim": consultation["fim"].strftime("%d/%m/%Y %H:%M"),
                "meet": consultation["meet_link"],
                "status": consultation["status"],
                "calendar_id": consultation.get("calendar_id"),
                "google_event_id": consultation.get("google_event_id"),
                "google_search_text": consultation.get("google_search_text"),
                "google_sync_status": consultation.get("google_sync_status"),
            })
        else:
            st.write("Nenhuma consulta futura encontrada.")
        
        st.markdown("### Propostas recebidas da psicóloga")

        pending_patient_proposals = get_pending_patient_proposals(psicologa_id, paciente_id)

        if pending_patient_proposals:
            selected_proposal_id = st.selectbox(
                "Propostas pendentes",
                options=[r["id"] for r in pending_patient_proposals],
                key="patient_pending_proposal_select",
                format_func=lambda rid: (
                    f"{PSYCHOLOGISTS[next(r for r in pending_patient_proposals if r['id'] == rid)['psicologa_id']]['nome']} - "
                    f"{next(r for r in pending_patient_proposals if r['id'] == rid)['old_start'].strftime('%d/%m %H:%M')}"
                )
            )

            proposal = next(r for r in pending_patient_proposals if r["id"] == selected_proposal_id)

            st.info(
                communication_text(
                    "psychologist_to_patient",
                    PSYCHOLOGISTS[proposal["psicologa_id"]]["nome"],
                    PATIENTS[proposal["paciente_id"]]["nome"],
                    proposal["old_start"],
                    proposal["suggestions"][0][0] if proposal["suggestions"] else None
                )
            )

            st.json({
                "psicóloga": PSYCHOLOGISTS[proposal["psicologa_id"]]["nome"],
                "consulta_original": proposal["old_start"].strftime("%d/%m/%Y %H:%M"),
                "status": proposal["status"],
                "mensagem_interna": proposal["raw_message"],
                 })

            if proposal["suggestions"]:
                patient_slot_labels = {
                    i: f"{slot[0].strftime('%d/%m %H:%M')} → {slot[1].strftime('%H:%M')}"
                    for i, slot in enumerate(proposal["suggestions"])
                }

                patient_selected_index = st.radio(
                    "Escolha um novo horário sugerido",
                    options=list(patient_slot_labels.keys()),
                    key=f"patient_proposal_radio_{proposal['id']}",
                    format_func=lambda i: patient_slot_labels[i]
                )
            else:
                patient_selected_index = None
                st.warning("Essa proposta não possui horários sugeridos.")

            patient_action_col1, patient_action_col2 = st.columns(2)

            with patient_action_col1:
                if st.button(
                    "Aceitar proposta e remarcar",
                    key=f"accept_patient_proposal_{proposal['id']}",
                    disabled=patient_selected_index is None,
                    width="stretch"
                ):
                    chosen = proposal["suggestions"][patient_selected_index]
                    updated, sync_info = apply_reschedule(
                        proposal["consultation_id"],
                        chosen[0],
                        chosen[1]
                    )

                    proposal["selected_slot"] = chosen
                    proposal["status"] = "concluido"

                    st.success("Proposta aceita e consulta remarcada com sucesso.")

                    patient_name = PATIENTS[proposal["paciente_id"]]["nome"]
                    psychologist_name = PSYCHOLOGISTS[proposal["psicologa_id"]]["nome"]
                    old_time_str = proposal["old_start"].strftime("%d/%m às %H:%M")
                    new_time_str = chosen[0].strftime("%d/%m às %H:%M")

                    if USE_GEMINI and GEMINI_AVAILABLE:
                        final_reply = generate_confirmation_with_gemini(
                            patient_name=patient_name,
                            psychologist_name=psychologist_name,
                            old_time=old_time_str,
                            new_time=new_time_str,
                        )
                        st.info(f"WhatsApp (simulado) • Assistente: {final_reply}")
                    else:
                        st.info(
                            communication_text(
                                "patient_confirmation",
                                psychologist_name,
                                patient_name,
                                proposal["old_start"],
                                chosen[0]
                            )
                        )

                    if sync_info["used_google"] and sync_info["success"]:
                        st.success(f"Google Calendar: {sync_info['message']}")
                    elif sync_info["used_google"] and not sync_info["success"]:
                        st.warning(f"Google Calendar: {sync_info['message']}")
                    else:
                        st.info(sync_info["message"])

                    st.json({
                        "evento_atualizado_local": updated["id"],
                        "novo_inicio": updated["inicio"].strftime("%d/%m/%Y %H:%M"),
                        "novo_fim": updated["fim"].strftime("%d/%m/%Y %H:%M"),
                        "google_event_id": updated.get("google_event_id"),
                        "google_sync_status": updated.get("google_sync_status"),
                        "last_sync_message": updated.get("last_sync_message"),
                    })

                    st.rerun()

            with patient_action_col2:
                if st.button(
                    "Recusar proposta",
                    key=f"reject_patient_proposal_{proposal['id']}",
                    width="stretch"
                ):
                    proposal["status"] = "recusado_pelo_paciente"
                    st.warning("A proposta foi recusada pelo paciente.")
                    st.rerun()
        else:
            st.write("Nenhuma proposta pendente da psicóloga para este paciente.")

# =============================
# Aba Psicóloga
# =============================
with psychologist_tab:
    st.subheader("Fluxos da psicóloga")
    sub1, sub2 = st.columns(2)

    with sub1:
        st.markdown("### Aprovar solicitação do paciente")
        pending_requests = [
            r for r in st.session_state.requests
            if r["status"] in ["aguardando_aprovacao", "aguardando_escolha_slot"]
        ]

        if pending_requests:
            selected_req_id = st.selectbox(
                "Solicitações abertas",
                options=[r["id"] for r in pending_requests],
                format_func=lambda rid: (
                    f"{summarize_request(next(r for r in pending_requests if r['id'] == rid))['paciente']} - "
                    f"{summarize_request(next(r for r in pending_requests if r['id'] == rid))['consulta_original']}"
                )
            )
            req = next(r for r in pending_requests if r["id"] == selected_req_id)
            st.json(summarize_request(req))

            if req["suggestions"]:
                slot_labels = {
                    i: f"{s[0].strftime('%d/%m %H:%M')} → {s[1].strftime('%H:%M')}"
                    for i, s in enumerate(req["suggestions"])
                }
                selected_index = st.radio(
                    "Escolha um novo horário",
                    options=list(slot_labels.keys()),
                    format_func=lambda i: slot_labels[i]
                )
            else:
                selected_index = None
                st.warning("Não encontrei sugestões automáticas. Para o MVP, ajuste as regras/agenda ou crie um novo cenário.")

            action_col1, action_col2 = st.columns(2)

            with action_col1:
                if st.button("Aprovar e remarcar", disabled=selected_index is None, use_container_width=True):
                    chosen = req["suggestions"][selected_index]
                    updated, sync_info = apply_reschedule(req["consultation_id"], chosen[0], chosen[1])

                    req["selected_slot"] = chosen
                    req["status"] = "concluido"

                    psy = PSYCHOLOGISTS[req["psicologa_id"]]
                    patient_name = PATIENTS[req["paciente_id"]]["nome"]

                    st.success("Consulta remarcada com sucesso.")

                    old_time_str = req["old_start"].strftime("%d/%m às %H:%M")
                    new_time_str = chosen[0].strftime("%d/%m às %H:%M")

                    if USE_GEMINI and GEMINI_AVAILABLE:
                        final_reply = generate_confirmation_with_gemini(
                            patient_name=patient_name,
                            psychologist_name=psy["nome"],
                            old_time=old_time_str,
                            new_time=new_time_str,
                        )
                        st.info(f"WhatsApp (simulado) • Assistente: {final_reply}")
                    else:
                        st.info(
                            communication_text(
                                "patient_confirmation",
                                psy["nome"],
                                patient_name,
                                req["old_start"],
                                chosen[0]
                            )
                        )

                    if sync_info["used_google"] and sync_info["success"]:
                        st.success(f"Google Calendar: {sync_info['message']}")
                    elif sync_info["used_google"] and not sync_info["success"]:
                        st.warning(f"Google Calendar: {sync_info['message']}")
                    else:
                        st.info(sync_info["message"])

                    st.json({
                        "evento_atualizado_local": updated["id"],
                        "novo_inicio": updated["inicio"].strftime("%d/%m/%Y %H:%M"),
                        "novo_fim": updated["fim"].strftime("%d/%m/%Y %H:%M"),
                        "meet_link": updated["meet_link"],
                        "google_event_id": updated.get("google_event_id"),
                        "google_sync_status": updated.get("google_sync_status"),
                        "last_sync_message": updated.get("last_sync_message"),
                    })

            with action_col2:
                if st.button("Recusar / manter horário", use_container_width=True):
                    req["status"] = "recusado"
                    st.warning("Solicitação recusada. A consulta foi mantida no horário original.")
        else:
            st.write("Nenhuma solicitação pendente.")

    with sub2:
        st.markdown("### Psicóloga inicia remarcação")

        psy_from = st.selectbox(
            "Psicóloga que quer remarcar",
            options=list(PSYCHOLOGISTS.keys()),
            format_func=lambda x: PSYCHOLOGISTS[x]["nome"],
            key="psy_from"
        )

        psy_consultations = [
            c for c in st.session_state.consultations
            if c["psicologa_id"] == psy_from and c["status"] == "agendada"
        ]

        if psy_consultations:
            selected_consultation_id = st.selectbox(
                "Consulta a remarcar",
                options=[c["id"] for c in psy_consultations],
                format_func=lambda cid: (
                    next(c for c in psy_consultations if c["id"] == cid)["titulo"]
                    + " — "
                    + next(c for c in psy_consultations if c["id"] == cid)["inicio"].strftime("%d/%m %H:%M")
                )
                )

            consultation = next(c for c in psy_consultations if c["id"] == selected_consultation_id)

            reason = st.text_input("Motivo interno", value="Ajuste de agenda da profissional")

            search_start_date = st.date_input(
                "Buscar horários a partir de",
                value=consultation["inicio"].date(),
                key="psy_search_start_date"
            )

            preferred_period_label = st.selectbox(
                "Período preferencial para propor",
                options=["qualquer", "manha", "tarde", "noite"],
                index=0,
                key="psy_preferred_period"
            )

            preferred_period = None if preferred_period_label == "qualquer" else preferred_period_label

            search_days = st.slider(
                "Janela de busca (dias)",
                min_value=1,
                max_value=60,
                value=14,
                key="psy_search_days"
            )

            proposal_suggestions = suggest_slots(
                psicologa_id=consultation["psicologa_id"],
                preference=preferred_period,
                start_date=search_start_date,
                days_ahead=search_days,
                limit=10
            )

            if proposal_suggestions:
                proposal_slot_labels = {
                    i: f"{slot[0].strftime('%d/%m %H:%M')} → {slot[1].strftime('%H:%M')}"
                    for i, slot in enumerate(proposal_suggestions)
                }

                selected_proposal_index = st.radio(
                    "Escolha o horário que será proposto ao paciente",
                    options=list(proposal_slot_labels.keys()),
                    key="selected_proposal_index",
                    format_func=lambda i: proposal_slot_labels[i]
                )
            else:
                selected_proposal_index = None
                st.warning("Nenhum horário disponível encontrado para esse período e janela de busca.")

            if st.button("Gerar proposta de remarcação", width="stretch", disabled=selected_proposal_index is None):
                chosen_proposal = proposal_suggestions[selected_proposal_index]

                req = create_reschedule_request(
                    origin="psychologist",
                    psicologa_id=consultation["psicologa_id"],
                    paciente_id=consultation["paciente_id"],
                    consultation_id=consultation["id"],
                    preference=preferred_period,
                    raw_message=reason,
                    suggestions=[chosen_proposal],
                    start_date=search_start_date,
                    days_ahead=search_days
                )

                req["status"] = "proposta_ao_paciente"

                psy = PSYCHOLOGISTS[consultation["psicologa_id"]]
                patient_name = PATIENTS[consultation["paciente_id"]]["nome"]

                st.success("Proposta de remarcação criada.")
                st.info(
                    communication_text(
                        "psychologist_to_patient",
                        psy["nome"],
                        patient_name,
                        req["old_start"],
                        chosen_proposal[0]
                    )
                )   
        else:
            st.write("Nenhuma consulta agendada para essa psicóloga.")

# =============================
# Aba Configuração
# =============================
with config_tab:
    st.subheader("Regras por psicóloga")
    cfg_psy = st.selectbox(
        "Escolha a psicóloga",
        options=list(PSYCHOLOGISTS.keys()),
        format_func=lambda x: PSYCHOLOGISTS[x]["nome"],
        key="cfg_psy"
    )
    psy = PSYCHOLOGISTS[cfg_psy]

    st.json({
        "nome": psy["nome"],
        "calendar_id": psy["calendar_id"],
        "duracao_min": psy["duracao_min"],
        "requer_aprovacao_remarcacao": psy["requer_aprovacao_remarcacao"],
        "dias_permitidos": psy["dias_permitidos"],
        "janelas": [f"{a.strftime('%H:%M')}-{b.strftime('%H:%M')}" for a, b in psy["janelas"]],
        "politica_cobranca": psy["politica_cobranca"],
        "tom": psy["tom"]
    })

    st.markdown("### Como isso escala")
    st.markdown(
        """
- Cada psicóloga pode ter regras próprias de agenda, cobrança e comunicação.
- Em produção, essas regras sairiam de uma base/configuração por clínica.
- O fluxo de atendimento usa essas regras para adaptar a tomada de decisão.
- A mesma estrutura pode futuramente integrar cobrança, prontuário e notificações externas.
- As skills podem ser modeladas por perfil, clínica ou profissional.
        """
    )

# =============================
# Aba Admin
# =============================
with admin_tab:
    st.subheader("Estado interno da demo")

    st.markdown("### Controle da demo")
    reset_col1, reset_col2 = st.columns(2)

    with reset_col1:
        if st.button("Resetar demo", width="stretch"):
            reset_demo_state()
            st.success("Demo resetada com sucesso.")
            st.rerun()

    with reset_col2:
        st.info("O reset volta apenas o estado local do app. Eventos já alterados no Google Calendar não são revertidos automaticamente.")
    
    st.markdown("### Consultas")
    st.dataframe([
        {
            "id": c["id"],
            "psicóloga": PSYCHOLOGISTS[c["psicologa_id"]]["nome"],
            "paciente": c["paciente_nome"],
            "início": c["inicio"].strftime("%d/%m/%Y %H:%M"),
            "fim": c["fim"].strftime("%d/%m/%Y %H:%M"),
            "status": c["status"],
            "meet": c["meet_link"],
            "calendar_id": c.get("calendar_id"),
            "google_event_id": c.get("google_event_id"),
            "google_search_text": c.get("google_search_text"),
            "google_sync_status": c.get("google_sync_status"),
            "last_sync_message": c.get("last_sync_message"),
        }
        for c in st.session_state.consultations
    ], use_container_width=True)

    st.markdown("### Solicitações")
    st.dataframe([
        {
            "id": r["id"],
            "origem": r["origin"],
            "psicóloga": PSYCHOLOGISTS[r["psicologa_id"]]["nome"],
            "paciente": PATIENTS[r["paciente_id"]]["nome"],
            "original": r["old_start"].strftime("%d/%m/%Y %H:%M"),
            "status": r["status"],
            "sugestões": len(r["suggestions"])
        }
        for r in st.session_state.requests
    ], use_container_width=True)

    st.markdown("### Ações rápidas")

    target_evt = next((c for c in st.session_state.consultations if c["id"] == "evt-1"), None)
    if target_evt:
        if st.button("Vincular evt-1 ao Google Calendar", use_container_width=True):
            event_id, msg = resolve_google_event_for_consultation(target_evt)
            if event_id:
                st.success(msg)
            else:
                st.warning(msg)
                
    st.markdown("### Exportação")

    export_df = build_requests_export_dataframe()

    if not export_df.empty:
        csv_data = export_df.to_csv(index=False).encode("utf-8-sig")

        st.download_button(
            label="Baixar solicitações em CSV",
            data=csv_data,
            file_name="solicitacoes_remarcacao.csv",
            mime="text/csv",
            width="stretch"
        )

        st.dataframe(export_df, width="stretch")
    else:
        st.info("Ainda não há solicitações para exportar.")

    st.markdown("### Próximos passos técnicos")
    st.markdown(
        """
1. Substituir a busca local de agenda por disponibilidade real com freeBusy.
2. Buscar eventos por paciente/psicóloga via API.
3. Atualizar eventos via API ao remarcar.
4. Plugar LLM para interpretação da mensagem natural.
5. Mover a orquestração para n8n.
6. Transformar regras em skills configuráveis por clínica/profissional.
        """
    )

st.divider()
st.caption(
    "MVP demonstrativo com dados fictícios. Quando disponível, a consulta pode ser vinculada ao Google Calendar para remarcação real."
)