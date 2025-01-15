# Development Setup

1) if on M1 OSX: ensure you have pretix/standlone built for arm64

    ```
    git clone https://github.com/pretix/pretix
    cd pretix
    docker build -t pretix/standalone:latest .
    ```

2) docker compose up -d

http://127.0.0.1:8000/control/
admin@localhost
admin



--------------

devenv up
   (keep open)
devenv shell
   init-pretix
   python setup.py develop
   cd .devenv/pretix/src
   python manage.py runserver


## Custom Invoice Rendering

### Problembeschreibung

Wir wollen, dass verschiedene Pretix-Produkte zusammengefasst als Gesamtsumme auf der
Rechnung erscheinen.

Beispiel 1:

```
1x NeosCon 2024 Early Bird Ticket
1x + Single Room Mi-Fr

auf Rechnung:
- 1x NeosCon 2024 Category B
```

Beispiel 2:

```
1x NeosCon 2024 Early Bird Ticket

auf Rechnung:
- 1x NeosCon 2024 Category A
```

Beispiel 3:

```
1x NeosCon 2024 Early Bird Ticket
1x + Single Room Di-Sa

auf Rechnung:
- 1x NeosCon 2024 Category B (!! anderer Preis als oben)
```

Beispiel 4:

```
NeosCon 2024 Early Bird Ticket
+ Double Room Di-Sa

NeosCon 2024 Early Bird Ticket
+ Double Room Di-Sa

NeosCon 2024 Early Bird Ticket

auf Rechnung:
- 1x NeosCon 2024 Category B
- 1x NeosCon 2024 Category B
- 1x NeosCon 2024 Category A
```

## Appetite:

so gering wie möglich, aber trotzdem korrekt (da invoicing)

## Lösungsskizze:

Variante A: custom Invoice Renderer
=> wird NICHT in DB persistiert (vorteil!)
=> existierender Erweiterungspunkt
=> wir müssen bestehende Invoice Rendering Klasse kopieren - RISIKO bei updates.

Variante B: Custom Invoice Line generator
=> wird dann auch in DB persistiert (nachteil!)
=> kA, wie man da rein kommt - ist das ein Erweiterungspunkt?
=> wir könnten den standard Invoice renderer verwenden (Vorteil!)

## Pitfalls

- Pretix Updates: Wir werden Pretix im relevanten Zeitraum NICHT updaten
  - (da das Risiko besteht, dass Invoice Rendering sich ändert
  - => wir schreiben den Code so, dass wir nur eine MINIMALE Codeänderung im Core machen => _group_key funktion in extra
       Methode in Klasse
- !!! the sum of the printed invoice items MUST be equal to the total sum. - Safeguard wenn wir an Invoice Lines rumschrauben
  - => wir vergleichen das berechnete Total mit self.invoice.order.total, wenn das abweicht => exception. Und Comment in Order ("needs attention")
  - (Dann gibts keine Rechnung -> das fällt auf!)
- müssen "irgendwie" mit mehreren Bestellungen desselben umgehen, und die auflisten. => macht Gruppierung schwieriger.
  - Testcases.
- Wir müssen REIHENFOLGE der Line Items berücksichtigen, da die Addons direkt nach dem Hauptprodukt kommen. Das ist wichtig,
  damit die Gruppierung beim Bestellen mehrerer Produkte korrekt funktioniert.  

## Concept

- line.item.meta_data['INVOICE_IS_MAINPRODUCT']: alle Items, welche als IS_SUBPRODUCT, die auf den so markierten Eintrag folgen, und zur selben Key gehören,
  bis zum nächsten IS_MAINPRODUCT werden zusammen gruppiert.
- line.item.meta_data['INVOICE_IS_SUBPRODUCT']: alle Items mit diesem Wert werden zu einer Zeile zusammen gruppiert.
- line.item.meta_data['INVOICE_MAINPRODUCT_NAME']: der Begriff, der auf der Rechnung erscheinen soll (mit der höchsten Priorität!)
- line.item.meta_data['INVOICE_MAINPRODUCT_NAME_PRIORITY'] -> die größte Zahl "gewinnt"

?? Übernachtungsprodukte mit mehreren Varianten oder nicht?
=> 1 Übernachtungsprodukt mit VARIANTEN -> da immer nur 1 Variante aktiv ist im Checkout. Besser von der Usability.

?? wie gehen wir mit versch. Zeitspannen um?
Einzelzimmer
  - !! Mi-Fr.
  - extra: Di-Mi
    - if workshop, early arrival
  - extra: Fr-Sa
    - if late workshop
  - extra: Sa-So
Doppelzimmer
  - !! Mi-Fr.
  - extra: Di-Mi
    - if workshop, early arrival
  - extra: Fr-Sa
    - if late workshop
  - extra: Sa-So

ausmultipliziert:
  - Mi-Fr
  - Mi-Sa
  - Mi-So
  - Di-Fr
  - Di-Sa
  - Di-So

=> 4x2 Varianten => BESSERE GUIDANCE.
=> 6x2 varianten

?? Checkin List ist nicht pro Variante, sondern pro Produkt.
=> wir brauchen für die Extra-Tage extra-Produkte, KEINE VARIANTEN !!!

=> adminssion product: nicht notwendig.

## Individual Steps

- [ ]