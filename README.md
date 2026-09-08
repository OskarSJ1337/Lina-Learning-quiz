# Lina – självtest

En svensk skrivbordsapp för Windows med 30 förståelse- och tillämpningsfrågor baserade på projektets tre PDF-filer. Fyra alternativ, grön/röd återkoppling, förklaring, sidhänvisning, Nästa-knapp och poängräknare. Frågor och svar blandas vid varje test. Missade frågor kan repeteras.

## Starta

Dubbelklicka på `dist/Lina-Sjalvtest.exe`. Ingen Python-installation, internetanslutning eller API-nyckel behövs. EXE-filen kan flyttas till en annan Windows-dator; frågebanken är inbyggd.

## PDF-läge

Välj **Läs PDF-filer och skapa fler begreppsfrågor** och markera en eller flera PDF-filer. Texten läses lokalt med pypdf. Meningar med kända kursbegrepp blir luckfrågor med fyra alternativ. Originalmening, filnamn och PDF-sida visas efter svaret. Detta är regelbaserad generering, inte en språkmodell som kan skapa fria resonemangsfrågor från valfritt innehåll. Skannade dokument utan textlager kräver OCR; ingen OCR ingår. Importerade frågor används under den aktuella sessionen och sparas inte.

Den inbyggda frågebanken är separat formulerad utifrån PDF-materialet. Sidhänvisningar räknas från PDF-filens första sida, inte bokens tryckta sidnummer. Övningsfrågorna är inte ett officiellt facit och täcker inte hela kursen. Original-PDF:erna packas inte in i EXE-filen.

## Utveckling

Python 3.13 användes för bygget. Tkinter ingår i standardinstallationen för Windows.

```powershell
python -m pip install -r requirements.txt
python app.py
python -m unittest -v
python -m PyInstaller --noconfirm --clean --onefile --windowed --name Lina-Sjalvtest --add-data "questions.json;." app.py
```

`questions.json` innehåller frågorna. `create_bank.py` återskapar den filen från de formulerade frågorna. `test_app.py` kontrollerar blandning, facit, låsta svar, poäng och repetition.
