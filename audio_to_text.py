import whisper

model = whisper.load_model("turbo")
result = model.transcribe("output.mp3", language="uk")
print(result["text"])