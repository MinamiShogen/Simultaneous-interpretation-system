from flask import Flask,render_template
from flask_sockets import Sockets
import whisper
from pydub import AudioSegment
import os
import threading

app = Flask(__name__)
sockets = Sockets(app)

model = whisper.load_model("tiny")

clockFlag = None


def clock():
    global clockFlag
    print("clock")
    clockFlag = 1
    
timer = threading.Timer(1, clock)

def save_as_mp3(data,filename):
    # Save the data as a WebM file
    # tempfile = ""
    # tempformatt = ""
    # if(type == "audio/webm"):
    #     tempfile = "temp.webm"
    #     tempformatt = "webm"
        
    # else:
    #     tempfile = "temp.mp4"
    #     tempformatt = "mp4"
    tempfile = "temp.webm"
    tempformatt = "webm"
    with open(tempfile, 'wb') as f:
        f.write(data)

    # Convert the WebM file to MP3
    audio = AudioSegment.from_file(tempfile, format=tempformatt)
    audio.export(filename, format='mp3')
    os.remove(tempfile)
    #print("delete webm")

def stitchMedia(filename):
    output_music = None
    if(os.path.exists('output.mp3')):
        input_music_1 = AudioSegment.from_mp3("output.mp3")
        input_music_2 = AudioSegment.from_mp3("seg.mp3")
        output_music = input_music_1 + input_music_2
    else:
        output_music = AudioSegment.from_mp3("seg.mp3")
        
    output_music.export("output.mp3", format="mp3")
    os.remove("seg.mp3")  


# Dictionary to hold incoming audio data for each WebSocket
ws_audio_data = {}

@sockets.route('/echo')
def echo_socket(ws):
    global ws_audio_data
    global clockFlag
    global timer
    # Initialize a new list to hold the audio data for this WebSocket
    ws_audio_data[ws] = []

    while not ws.closed:

        
        audio_data = ws.receive()
        #print(clockFlag)
        if(audio_data == "START_RECORDING"):
            timer.start()
        elif(audio_data == "STOP_RECORDING" or clockFlag == 1):
            clockFlag = 0
            # Process the audio data if a "STOP_RECORDING" message is received
            full_audio_data = b''.join(ws_audio_data[ws])
            del ws_audio_data[ws]



            save_as_mp3(full_audio_data,"seg.mp3")

            stitchMedia("seg.mp3")
            result = model.transcribe("output.mp3")
            print(result["text"])
            ws.send(result["text"])

            # Reset the audio data for this WebSocket
            ws_audio_data[ws] = []

            if(audio_data == "STOP_RECORDING"):
                timer.cancel()
                clockFlag = 0


        else:
            # Add the incoming audio data to the list for this WebSocket
            ws_audio_data[ws].append(audio_data)

            # # load audio and pad/trim it to fit 30 seconds
            # audio = whisper.load_audio("output.mp3")
            # audio = whisper.pad_or_trim(audio)

            # # make log-Mel spectrogram and move to the same device as the model
            # mel = whisper.log_mel_spectrogram(audio).to(model.device)

            # # decode the audio
            # options = whisper.DecodingOptions()
            # result = whisper.decode(model, mel, options)

            # # send the recognized text to the client
            # ws.send(result.text)

            # # Remove the audio data for this WebSocket
            # del ws_audio_data[ws]

@app.route('/')
def hello_world():
    return render_template("index.html")


@app.errorhandler(Exception)
def handle_exception(e):
    os.remove("output.mp3")
    



if __name__ == '__main__':
    from gevent import pywsgi
    from geventwebsocket.handler import WebSocketHandler
    server = pywsgi.WSGIServer(('0.0.0.0', 8000), app, handler_class=WebSocketHandler)
    # empty_segment = AudioSegment.empty()
    # empty_segment.export("output.mp3", format="mp3")
    
    clockFlag = 0
    print('server start')
    server.serve_forever()

