from google_calendar_service import find_event_by_text, update_event_time

event = find_event_by_text("primary", "TESTE MV")

if not event:
    print("Evento não encontrado.")
else:
    updated = update_event_time(
        calendar_id="primary",
        event_id=event["id"],
        new_start_iso="2026-03-27T10:00:00-03:00",
        new_end_iso="2026-03-27T10:50:00-03:00",
    )

    print("Evento atualizado com sucesso:")
    print("ID:", updated["id"])
    print("Novo início:", updated["start"])
    print("Novo fim:", updated["end"])