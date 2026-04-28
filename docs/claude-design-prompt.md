# AcePad — Design Brief dla Claude `/frontend-design`

## Jak używać

1. W Claude Code (w tym repo) wywołaj: `/frontend-design`
2. Wklej brief poniżej
3. Claude najpierw zada pytania o **purpose / tone / constraints / differentiation** — odpowiadaj konkretnie
4. Po wygenerowaniu nowego UI iteruj: `/baseline-ui` (usuwa AI slop), potem `/fixing-accessibility`, potem `/fixing-motion-performance`

**Ważne:** zanim puścisz redesign na całą apkę — puść **na jeden ekran** (np. Calibration Wizard albo Training Overlay), zobacz efekt, dopasuj, dopiero potem rozciągaj na resztę.

---

## BRIEF (gotowy do wklejenia)

```
Redesign UI aplikacji AcePad — klienta do zdalnego sterowania robotem
pingpongowym Donic Robopong 3050XL. Nie rób generycznego "AI slop UI".

═══════════════════════════════════════════════════════════════════
KONTEKST (purpose)
═══════════════════════════════════════════════════════════════════
• AcePad zastępuje oficjalną aplikację Newgy — alternatywny klient, który
  daje graczowi pełną kontrolę nad parametrami rzutu robota.
• Użytkownik: ping-pong player, 20-60 lat, stoi przy stole z rakietką
  w dłoni, pot na czole, telefon wystawiony na statywie 1.5-3 m od twarzy.
• Kluczowe scenariusze użycia:
  1) Kalibracja (jednorazowa po ustawieniu robota) — wizard z SVG stołem,
     d-pad ustawia oscillation, top_speed, rotation.
  2) Training — płynny przepływ treningu, overlay z liczbą piłek
     i countdown-em MUSI BYĆ CZYTELNY Z 3 METRÓW (gracz nie podchodzi
     do telefonu między piłkami).
  3) Szybkie "Solo Shot" — user klika raz, robot rzuca jedną piłkę,
     gracz oddaje, powtarza.
  4) Serves library — przeglądanie serwisów pogrupowanych techniką.

═══════════════════════════════════════════════════════════════════
AESTHETIC / TONE
═══════════════════════════════════════════════════════════════════
Zaproponuj jeden z kierunków i uzasadnij wybór. Moja pierwsza myśl:
"industrial / utilitarian + sports performance" — coś pomiędzy kokpitem
maszyny a tablicą wyników na hali. Unikaj "startup SaaS dashboard".

Inne możliwości do rozważenia:
• editorial / magazine (typografia jako bohater, traktuj drille jak
  rozdziały książki)
• brutalist / raw (mono font, surowe linie, kontrast 100/900 waga)
• retro-futuristic arcade (jak konsole lat 80., neony, pixel-perfect
  border-rings) — pasuje do "maszyna vs człowiek"

Przedstaw konkretną rekomendację, nie listę możliwości.

═══════════════════════════════════════════════════════════════════
CONSTRAINTS (twarde, nie negocjowalne)
═══════════════════════════════════════════════════════════════════
• Stack: Vue 3 CDN (vue.global.prod.js), single-file index.html.
  NIE MA build-step-u (no Vite, no webpack). Każdy komponent musi
  działać bez kompilacji.
• Wszystko musi siedzieć w jednym index.html + style.css + manifest.json.
  Logika w <script> w setup() Composition API.
• i18n: każdy tekst UI przez t('klucz'), treści drilli przez tc(type,key).
  Obsługiwane języki: PL/EN/DE/FR/ZH. t() jest globalProperty — nie
  zwracaj jej z setup() (Vue 3 prod compiler to złamie).
• Mobile-first, max-width 680px, safe-area insets, touch target 44x44px.
• Dark theme. Podstawa #0f1117, ale paleta CSS custom properties.
• PWA: manifest.json, standalone display mode.
• Backend API: REST /api/* + WebSocket /ws — nie zmieniaj kontraktów.
• Training overlay (page=training, po starcie treningu) — licznik piłek
  i pozostały czas MUSZĄ być czytelne z 3m: minimum 48px dla głównej
  liczby, kontrast AAA.
• Ikony są konwencją — NIE ZMIENIAJ:
  ⏱ (czas), 🎥+REC (nagrywanie), ⏸/⏹/▶ (pauza/stop/play),
  💬 (notatka), 🎙 (mikrofon), 🎾 (serwisy).

═══════════════════════════════════════════════════════════════════
DIFFERENTIATION — co ma być niezapomniane
═══════════════════════════════════════════════════════════════════
Chcę żeby gracz, który zobaczy AcePad raz, zapamiętał konkretny moment.
Propozycje (wybierz jedną, zaproponuj lepszą):
• "Ball Counter" w treningu — każda rzucona piłka = mocny tick w HUD
  (typograficzna eksplozja, slot-machine roll, cokolwiek co sprawia
  że counter FEEL'uje mechanicznie-cielesnie, nie jak zwykły span).
• Kalibracja SVG stołu — zamiast statycznej grafiki, stół żyje:
  ball trails, parallax robota przy zmianie rotation, efekt "thrown"
  piłki po każdym teście kalibracyjnym.
• Connect screen — nie lista urządzeń jak w settingsach BT, tylko
  "radar scan" z uwyraźnieniem robota Donic (jest tylko jeden typ).

═══════════════════════════════════════════════════════════════════
CO MASZ NIE ROBIĆ
═══════════════════════════════════════════════════════════════════
• Żadnego Inter, Roboto, Arial, system-ui fontu — wybierz coś
  z charakterem (JetBrains Mono / Space Grotesk / Bricolage Grotesque /
  Chakra Petch dla technicznego sportowego feelu).
• Żadnych purple gradientów, żadnego "linear-gradient(135deg, #667eea, #764ba2)".
• Żadnych Tailwindowych cards z rounded-xl + shadow-lg + p-6. Nie chcemy
  SaaS dashboard look.
• Żadnych generycznych ikonek Lucide/Heroicons dla podstawowych akcji —
  typografia i emoji konwencja są bohaterami.
• Żadnego framer-motion, lottie, motion-library zależności — tylko CSS
  animations / transitions (no-build constraint).
• Training overlay nie może mieć "subtle micro-interactions" — musi
  być bold, odczyt z 3m, nie finessy.

═══════════════════════════════════════════════════════════════════
ZAKRES PIERWSZEJ ITERACJI (1 ekran)
═══════════════════════════════════════════════════════════════════
Zaczynamy od CALIBRATION WIZARD (frontend/index.html linie 558-734
oraz frontend-v2/index.html linie ~520-700). To najważniejszy pierwszy
kontakt użytkownika z robotem — jeśli tu go zachwyci, reszta pójdzie.

Pokaż mi:
1) Propozycję aesthetic direction z uzasadnieniem (3-5 zdań)
2) Moodboard słowny: fonty, paleta kolorów jako CSS vars, key motions
3) Gotowy HTML+CSS dla całego wizarda — drop-in do frontend-v2/
4) Lista rzeczy które rozrzucimy na resztę apki jeśli ten kierunek
   zostanie zaakceptowany (typography scale, spacing scale, motion tokens)

Plik docelowy: /tmp/acepad-cal-wizard-redesign.html (standalone preview)
Potem zdecyduję czy chcę żebyś przeniósł to do frontend-v2/index.html.

Zacznij od pytań których odpowiedzi potrzebujesz zanim zaczniesz pisać
kod. Nie pisz kodu zanim dostaniesz odpowiedzi.
```

---

## Po pierwszej iteracji

Gdy dostaniesz wizarda i zaakceptujesz kierunek:

**Ekran 2 — Training Overlay** (najkrytyczniejszy UX)
```
Teraz zaaplikuj ten sam design language do ekranu Training (page='training').
Kluczowe wymagania: ball counter i countdown czytelne z 3m. Reszta HUD
(notatki, mikrofon, percent override, skip/pause/stop) mniej prominentny.
Odniesienie: aerospace HUD, sports scoreboard, fighting game combo counter.
```

**Ekran 3 — Connect (radar)**
```
Rozłożone na Connect. Aktualnie to nudna lista. Chcę "radar scan"
z kontekstem że szukamy JEDNEGO konkretnego robota Donic, nie dowolnego
BLE device.
```

**Baseline pass**
```
/baseline-ui — przejdź po wszystkich ekranach, napraw spacing (używaj
jednej skali: 4/8/16/24/40/64), typography scale (3 rozmiary max
per ekran), states (hover/active/disabled consistent).
```

**Accessibility pass**
```
/fixing-accessibility — keyboard nav, focus rings widoczne w dark,
aria-label dla emoji buttons, kontrast 4.5:1 minimum, 7:1 dla
critical readouts (ball counter).
```

---

## Przydatne linki

- [Improving frontend design through Skills — Claude blog](https://claude.com/blog/improving-frontend-design-through-skills)
- [Prompting for frontend aesthetics — Claude Cookbook](https://platform.claude.com/cookbook/coding-prompting-for-frontend-aesthetics)
- [frontend-design SKILL.md (Anthropic GitHub)](https://github.com/anthropics/claude-code/blob/main/plugins/frontend-design/skills/frontend-design/SKILL.md)
- [Using Claude Design for prototypes and UX](https://claude.com/resources/tutorials/using-claude-design-for-prototypes-and-ux)
