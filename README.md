# Fast Whisper v2

**Fast Whisper v2** är en snabb och användarvänlig applikation för ljudtranskribering, byggd med **Faster Whisper**. Applikationen erbjuder enkel hantering av ljudtranskriptioner och stödjer realtidsinspelning via mikrofon eller datorljud.

## Funktioner

- **Snabb & exakt transkribering**: Använder **Faster Whisper** för effektiv taligenkänning.
- **Flexibel ljudinspelning**: Stöd för **mikrofon**, **datorljud**, eller **båda** samtidigt.
- **Anpassningsbar hotkey-styrning**: Möjlighet att styra inspelning med tangentbordsgenvägar.
- **Dynamisk temahantering**: Stöd för ljusa och mörka teman.
- **Automatisk modellcachning**: Laddar Whisper-modellen effektivt för optimerad prestanda.
- **GUI-stöd med PySide6**: En lättanvänd grafisk användargränssnitt.

---

## Installation

### 1. Krav
- **Python 3.10**  
- **Pip och Virtual Environment**  

### 2. Installera Fast Whisper v2

#### a) Klona repositoryt:
```sh
git clone https://github.com/rewnozom/fast_whisper.git
cd fast_whisper
```

#### b) Skapa och aktivera en virtuell miljö:
På Windows:
```sh
python -m venv env
env\Scripts\activate
```
På macOS/Linux:
```sh
python3 -m venv env
source env/bin/activate
```

#### c) Installera beroenden:
```sh
pip install -r requirements.txt
```
**Alternativ:** Använd `setup.py` för att automatiskt hantera installationen:
```sh
python setup.py install
```

---

## Användning

### 1. Starta applikationen:
```sh
python -m fast_whisper_v2
```
Alternativt kan du använda CLI-kommandot:
```sh
fast-whisper
```

### 2. Välj modell och inställningar:
- Standardmodellen är **"tiny"**, men du kan ändra den i `config.json` eller i GUI:t.
- Inspelning kan ske via **mikrofon**, **datorljud**, eller **båda**.

### 3. Transkribera ljud:
1. Tryck på **hotkey** (standard: `§`) för att börja spela in.
2. Släpp knappen för att stoppa och påbörja transkribering.
3. Texten visas automatiskt i GUI:t.

---

## Konfigurationsinställningar

Konfigurationen lagras i `config.json`. Exempel:

```json
{
    "model_name": "tiny",
    "device": "cpu",
    "compute_type": "float32",
    "audio_format": "Int16",
    "channels": 1,
    "rate": 16000,
    "chunk": 1024,
    "wave_output_filename": "output.wav",
    "speak_hotkey": "§",
    "default_window_size": "500x600",
    "input_source": "microphone"
}
```
**Justeringar:**  
- Ändra `model_name` till `"base"`, `"small"`, `"medium"`, `"large"` beroende på behov.
- `input_source`: `"microphone"`, `"computer_audio"`, eller `"both"`.
- `speak_hotkey`: Byt ut mot valfri tangent.


---

## Felsökning

**Problem:**  
- _"No module named PySide6"_  
  **Lösning:** `pip install PySide6`

- _"OSError: [Errno -9996] Invalid input device (no default output device)"_  
  **Lösning:** Kontrollera att en ljudenhet är ansluten och välj en enhet i `config.json`.

- _"Pyaudio fungerar inte på Windows"_  
  **Lösning:** Installera PyAudio manuellt:  
  ```sh
  pip install pipwin
  pipwin install pyaudio
  ```

