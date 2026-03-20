# Instrukcje dla Claude — robopong-app

## Kontekst projektu

Ten projekt to **autorska aplikacja zastępująca Newgy** dla robota pingpongowego Donic Robopong 3050XL.
Celem jest stworzenie własnego klienta, który komunikuje się z robotem i daje pełną kontrolę nad jego parametrami.

## Zasady pracy

### Zarządzanie zadaniami (OBOWIĄZKOWE)
- Gdy użytkownik mówi "dodaj zadanie", "nowe zadanie", "task:", "TODO:" lub prosi o dodanie czegoś do listy zadań — **zawsze** twórz GitHub Issue
- Repozytorium: `tomekniemczyk/robopong-app`
- Komenda: `gh issue create --repo tomekniemczyk/robopong-app --title "..." --body "..." --label "backlog,PRIORYTET"`
- Priorytety (etykiety): `wysoki`, `sredni`, `niski` — domyślnie `sredni`
- Nowe zadania zawsze dostają etykietę `backlog`
- Zmiana statusu: zamień etykietę na `w-toku` lub `gotowe` (przez `gh issue edit --add-label / --remove-label`)

### Komunikacja z robotem
- Protokół komunikacji z Robopong 3050XL jest **do zbadania** — nie zakładaj niczego
- Pierwsze zadanie to reverse engineering — analiza jak Newgy się łączy (USB, Bluetooth, WiFi?)
- Dokumentuj każde odkrycie w odpowiednim pliku w repozytorium

### Styl kodu
- Zwięzły, bez nadmiarowych komentarzy
- Brak nadmiarowej obsługi błędów dla scenariuszy niemożliwych
- Bez feature flags, backward-compat shims itp.

### Komunikacja
- Odpowiedzi po polsku, chyba że kod/nazwy techniczne wymagają angielskiego
- Krótko i na temat
- Nie podsumowuj tego co właśnie zrobiłeś — użytkownik widzi diff

## Slash commands

- `/task [opis]` — dodaj nowe zadanie do TASKS.md
- `/tasks` — pokaż aktualny stan TASKS.md
