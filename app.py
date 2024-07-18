import azure.cognitiveservices.speech as speechsdk
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import uuid
import os

app = Flask(__name__)
CORS(app)


speech_key = os.environ.get('n_api_key')
translator_key = os.environ.get('translation_key')
service_region = os.environ.get('region')


def transcribe_audio_to_text(preferred_language, audio_file_path):
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
    audio_config = speechsdk.audio.AudioConfig(filename=audio_file_path)
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config, language="hi-IN" if preferred_language == "hindi" else "en-US")

    result = speech_recognizer.recognize_once()

    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        return result.text
    else:
        return None

def translate_text(text, target_language):
    endpoint = "https://api.cognitive.microsofttranslator.com/translate"
    params = {
        "api-version": "3.0",
        "to": target_language
    }
    headers = {
        "Ocp-Apim-Subscription-Key": translator_key,
        "Ocp-Apim-Subscription-Region": service_region,
        "Content-type": "application/json",
        "X-ClientTraceId": str(uuid.uuid4())
    }
    body = [{"text": text}]

    response = requests.post(endpoint, params=params, headers=headers, json=body)
    if response.status_code == 200:
        translations = response.json()
        return translations[0]["translations"][0]["text"]
    else:
        return None

def synthesize_text_to_speech(text, language, output_audio_path):
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
    voice_name = "hi-IN-MadhurNeural" if language == "hindi" else "en-IN-NeerjaNeural"
    speech_config.speech_synthesis_voice_name = voice_name
    audio_config = speechsdk.audio.AudioOutputConfig(filename=output_audio_path)
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)

    result = synthesizer.speak_text_async(text).get()
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return output_audio_path
    else:
        return None

@app.route('/transcribe', methods=['POST'])
def transcribe():
    preferred_language = request.form['preferred_language']
    audio_file = request.files['audio_file']
    audio_path = os.path.join('uploads', audio_file.filename)
    audio_file.save(audio_path)

    text = transcribe_audio_to_text(preferred_language, audio_path)
    if text:
        if preferred_language == "hindi":
            translated_text = translate_text(text, "en")
            if translated_text:
                return jsonify({'transcription': translated_text})
            else:
                return jsonify({'error': 'Translation failed'}), 500
        else:
            return jsonify({'transcription': text})
    else:
        return jsonify({'error': 'Transcription failed'}), 500

@app.route('/synthesize', methods=['POST'])
def synthesize():
    preferred_language = request.form['preferred_language']
    input_text = request.form['text']
    output_audio_path = os.path.join('outputs', 'output.wav')

    if preferred_language == "hindi":
        translated_text = translate_text(input_text, "hi")
        if translated_text:
            audio_path = synthesize_text_to_speech(translated_text, "hindi", output_audio_path)
        else:
            return jsonify({'error': 'Translation failed'}), 500
    else:
        audio_path = synthesize_text_to_speech(input_text, "english", output_audio_path)

    if audio_path:
        return jsonify({'audio_file': audio_path})
    else:
        return jsonify({'error': 'Synthesis failed'}), 500

if __name__ == '__main__':
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('outputs', exist_ok=True)
    app.run(debug=True)
