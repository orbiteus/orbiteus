# Moduł social — Specification

> Status: TODO (Faza 2)
> depends_on: [base]

---

## Cel modułu

Social layer dla każdego modelu danych w systemie.
Trzy funkcjonalności: Chatter, Activities, Notifications.
Każdy model który chce mieć te funkcje dodaje je przez mixin — bez zmian w kodzie modelu.

---

## 1. Chatter (komentarze per rekord)

### Koncepcja
Każdy rekord w systemie może mieć powiązane wiadomości. Jeden model `Message` obsługuje wszystkie.

### Model: Message
```python
id, tenant_id,
model_name,     # np. "crm.opportunity"
record_id,      # UUID rekordu
message_type,   # "comment" | "note" | "system" | "email"
author_id,      # FK → base_users
body,           # treść (HTML lub plain text)
parent_id,      # reply threading
attachments: list[UUID],  # FK → base_ir_attachments
create_date
```
Tabela: `social_messages`
Indeks: (model_name, record_id) — kluczowy dla wydajności

### API
```
GET  /api/social/messages?model=crm.opportunity&record_id={uuid}
POST /api/social/messages  {model_name, record_id, body, message_type}
DELETE /api/social/messages/{id}
```

### UI — Chatter component
Wyświetlany na dole każdego formularza rekordu.
```tsx
<Chatter modelName="crm.opportunity" recordId={record.id} />
```
Zawiera:
- Lista wiadomości (reverse chronological)
- Pole "Dodaj komentarz" (+ załączniki)
- System messages (zmiana etapu, przypisanie usera itp.)

---

## 2. Activities (zadania per rekord)

### Koncepcja
Aktywności to zaplanowane działania powiązane z rekordem.
Typy: phone call, email, meeting, todo, upload document.
Każda aktywność ma deadline i assignee.

### Model: ActivityType
Konfigurowalne typy aktywności.
```python
id, name, icon, color,
default_user_id,
delay_count, delay_unit,    # domyślny termin (np. "2 days")
category                    # "upload" | "phonecall" | "meeting" | "email" | "todo"
```
Tabela: `social_activity_types`
Seed: 5 domyślnych typów przy instalacji modułu.

### Model: Activity
```python
id, tenant_id,
model_name,
record_id,
activity_type_id,
user_id,           # assignee
summary,           # krótki opis
note,              # dłuższa notatka
deadline,          # data wykonania
done_date,         # data wykonania (NULL = niewykonana)
feedback,          # notatka po wykonaniu
create_date
```
Tabela: `social_activities`

### API
```
GET    /api/social/activities?model=crm.opportunity&record_id={uuid}
GET    /api/social/activities/my              → moje aktywności (calendar feed)
POST   /api/social/activities                 → zaplanuj aktywność
PUT    /api/social/activities/{id}
POST   /api/social/activities/{id}/done       → {feedback} → oznacz jako wykonana
DELETE /api/social/activities/{id}
```

### UI — Activity bar
Wyświetlany w każdej liście (kolumna z ikonkami aktywności) i w formularzu.
```tsx
<ActivityBar modelName="crm.opportunity" recordId={record.id} />
```

---

## 3. Notifications (in-app)

### Koncepcja
Powiadomienia systemowe i user-generated. Real-time via SSE (Server-Sent Events).

### Model: Notification
```python
id, tenant_id,
user_id,           # odbiorca
title,
body,
notification_type, # "activity_reminder" | "mention" | "assignment" | "system"
model_name,
record_id,         # link do rekordu (opcjonalny)
is_read,
create_date
```
Tabela: `social_notifications`

### API
```
GET  /api/social/notifications              → lista (unread first)
POST /api/social/notifications/{id}/read   → oznacz jako przeczytane
POST /api/social/notifications/read-all    → wszystkie przeczytane
GET  /api/social/notifications/stream      → SSE endpoint (real-time)
```

### SSE endpoint
```
GET /api/social/notifications/stream
Authorization: Bearer {token}
Content-Type: text/event-stream

data: {"type": "notification", "id": "...", "title": "...", "body": "..."}
```

### UI — NotificationBell
W AppShell header (obok user menu).
```tsx
<NotificationBell />
```
- Badge z liczbą nieprzeczytanych
- Dropdown z listą ostatnich
- Auto-connect SSE po zalogowaniu

---

## Integracja z modułami

Dowolny moduł może używać social layer bez żadnych zmian w swoich tabelach:

```python
# W services.py modułu crm:
from modules.social.services import log_message, create_activity, notify_user

# Po zmianie etapu okazji:
await log_message(session, ctx, "crm.opportunity", opportunity.id,
                  f"Etap zmieniony na: {new_stage.name}", "system")

await notify_user(session, ctx, opportunity.assigned_user_id,
                  "Przypisano Ci okazję", f"Okazja: {opportunity.name}",
                  "crm.opportunity", opportunity.id)
```

---

## Status

| Komponent | Status |
|---|---|
| Message model + API | TODO |
| Activity model + API | TODO |
| Notification model + API | TODO |
| SSE stream | TODO |
| Chatter UI component | TODO |
| Activity bar UI | TODO |
| NotificationBell UI | TODO |
