Pokaż aktualny stan boardu zadań z GitHub Issues.

Wykonaj poniższe komendy i wyświetl wyniki w czytelny sposób:

gh issue list --repo tomekniemczyk/robopong-app --label "backlog" --state open
gh issue list --repo tomekniemczyk/robopong-app --label "w-toku" --state open
gh issue list --repo tomekniemczyk/robopong-app --label "gotowe" --state all

Podsumuj: ile zadań w Backlog / W toku / Gotowe.
