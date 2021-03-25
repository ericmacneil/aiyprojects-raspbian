#!/usr/bin/env python3
# Copyright 2017 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Run a recognizer using the Google Assistant Library.
The Google Assistant Library has direct access to the audio API, so this Python
code doesn't need to record audio. Hot word detection "OK, Google" is supported.
The Google Assistant Library can be installed with:
    env/bin/pip install google-assistant-library==0.0.2
It is available for Raspberry Pi 2/3 only; Pi Zero is not supported.
"""

import logging
import subprocess
import sys

import os
import signal
import requests
import re

import aiy.assistant.auth_helpers
import aiy.audio
import aiy.voicehat
from google.assistant.library import Assistant
from google.assistant.library.event import EventType

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
)

station_list = {
    #WNYC
    'npr' : 'http://www.wnyc.org/stream/wnyc-fm939/mp3.pls',
    #Bassdrive DnB Radio
    'drum and bass' : 'http://bassdrive.com/bassdrive.m3u',
    #Soma FM DefCon Radio
    'soma fm' : 'http://somafm.com/defcon256.pls',
    #CodeSouth Radio
    'code south' : 'http://s1.viastreaming.net/7150/listen.m3u',
    #BBC World News
    'bbc' : 'http://www.vpr.net/vpr_files/stream_playlists/vpr_bbc_mp3.pls'
}

def btc_price():
    # use this with requests
    # r = requests.get('https://api.coinbase.com/v2/prices/spot?currency=USD')
    r = subprocess.check_output('curl https://api.coinbase.com/v2/prices/spot?currency=USD', shell=True)
    p = re.compile('\d')
    # use this with requests
    # r = ''.join(p.findall(r.text))
    r = ''.join(p.findall(str(r)))
    cents = r[-2:]
    dollars = r[:-2]
    aiy.audio.say('Current Price: ' + dollars + ' dollars and ' + cents + 'cents')
    return

#Turn up volume 10%
def turn_it_up():
    subprocess.call("amixer -q sset 'Master' 10%+", shell=True)
    return

#Turn down volume 10%
def turn_it_down():
    subprocess.call("amixer -q sset 'Master' 10%-", shell=True)
    return

#Returns station url based on key query
def stations(station_search):
    print('searching for: %s' % station_search)
    print('Playing: %s' % station_list[station_search])
    return station_list[station_search]

#Says a list of all radio stations
def list_stations():
    for item in station_list.keys():
        aiy.audio.say(item)
    return

def power_off_pi():
    aiy.audio.say('Good bye!')
    subprocess.call('sudo shutdown now', shell=True)

def reboot_pi():
    aiy.audio.say('See you in a bit!')
    subprocess.call('sudo reboot', shell=True)

#Plays audio stream via VLC
def play_stream(stream_name, stream_url):
    aiy.audio.say('Playing ' + stream_name)
    button = aiy.voicehat.get_button()
    p = subprocess.Popen('cvlc ' + stream_url, stdin=subprocess.PIPE, shell=True, preexec_fn=os.setsid)
    while not button.wait_for_press():
        os.killpg(os.getpgid(p.pid), signal.SIGTERM)
        return

def say_ip():
    ip_address = subprocess.check_output("hostname -I | cut -d' ' -f1", shell=True)
    aiy.audio.say('My IP address is %s' % ip_address.decode('utf-8'))

def process_event(assistant, event):
    status_ui = aiy.voicehat.get_status_ui()
    if event.type == EventType.ON_START_FINISHED:
        status_ui.status('ready')
        if sys.stdout.isatty():
            print('Say "OK, Google" then speak, or press Ctrl+C to quit...')

    elif event.type == EventType.ON_CONVERSATION_TURN_STARTED:
        status_ui.status('listening')

    elif event.type == EventType.ON_RECOGNIZING_SPEECH_FINISHED and event.args:
        print('You said:', event.args['text'])
        text = event.args['text'].lower()
        if text == 'power off':
            assistant.stop_conversation()
            power_off_pi()
        elif text == 'reboot':
            assistant.stop_conversation()
            reboot_pi()
        elif text == 'ip address':
            assistant.stop_conversation()
            say_ip()
        elif text == 'turn it up':
            assistant.stop_conversation()
            turn_it_up()
        elif text == 'turn it down':
            assistant.stop_conversation()
            turn_it_down()
        #If first 5 characters of text are play
        elif text[:5] == 'play ':
            assistant.stop_conversation()
            #Search 'stations' for the text and plays that station
            station = text[5:]
            station_url = stations(station)
            play_stream(station, station_url)
        elif text == 'list stations':
            assistant.stop_conversation()
            list_stations()
        elif text == 'bitcoin price':
            assistant.stop_conversation()
            btc_price()

    elif event.type == EventType.ON_END_OF_UTTERANCE:
        status_ui.status('thinking')

    elif event.type == EventType.ON_CONVERSATION_TURN_FINISHED:
        status_ui.status('ready')

    elif event.type == EventType.ON_ASSISTANT_ERROR and event.args and event.args['is_fatal']:
        sys.exit(1)


def main():
    credentials = aiy.assistant.auth_helpers.get_assistant_credentials()
    with Assistant(credentials) as assistant:
        for event in assistant.start():
            process_event(assistant, event)


if __name__ == '__main__':
    main()
