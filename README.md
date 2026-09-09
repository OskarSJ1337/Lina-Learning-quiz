# Linas självstudie quiz

En svensk quizapp för Vetenskaplig metodkurs Speciallärar- och specialpedagogprogrammet. Frågebanken innehåller 98 frågor från fyra PDF-filer, med fyra svarsalternativ, enkla förklaringar och källhänvisningar.

## Starta

Dubbelklicka på `dist/Lina-Sjalvtest.exe`. Appen körs lokalt på 64-bitars Windows utan installation, internet eller Python. Skicka bara EXE-filen; frågorna ingår och kursens PDF-filer behövs inte för att spela.

Startsidan har ett val för alla frågor och ett för varje källa. Åsberg (2001) har 16 frågor om bland annat metod, dataform, kunskapssyn och textens kritik av uppdelningen i kvalitativa och kvantitativa metoder. Författarens ståndpunkter anges i frågorna.

Förenkla frågan visar en lättare formulering. Dag- och nattläge finns. Det går att hoppa över frågor och gå tillbaka. Sidhänvisningar räknas från PDF-filens första sida.

## Utveckling

Python 3.13 med Tkinter används.

```powershell
python -m pip install -r requirements.txt
python create_bank.py
python -m unittest -v
python app.py
python build_exe.py
```

`aasberg_questions.json` innehåller den nya källans frågor, förenklingar och svarsförklaringar. `create_bank.py` sammanställer hela banken i `questions.json`, som bäddas in vid bygget. Källmaterial i PDF- och HTML-format samt byggfiler ignoreras av Git.
