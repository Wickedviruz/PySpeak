from gtts import gTTS
from pydub import AudioSegment

# Text to be converted to speech
text = "This is a test sound"

# Create the gTTS object
tts = gTTS(text, lang='en')

# Save the audio file
tts.save("test_sound.mp3")

# Convert MP3 to WAV format using pydub
#audio = AudioSegment.from_mp3("test_sound.mp3")
#audio.export("test_sound.wav", format="wav")
