#!/usr/bin/env python
import configparser
import requests
import json
import logging
import time
import os
from datetime import datetime
from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics # type: ignore

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', handlers=[logging.FileHandler('app.log'), logging.StreamHandler()])
logger = logging.getLogger(__name__)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logger.info('welcome to buspi!')
logger.info('begin logging...')

class BusClock:
    def __init__(self):
        logger.info('__init__ begin')
        self.url = []
    
    def setup_display(self):
        logger.info('setup_display begin')
        self.options = RGBMatrixOptions()
        self.options.rows = 32
        self.options.cols = 64
        self.options.hardware_mapping = 'adafruit-hat'
        self.options.gpio_slowdown = 3 
        self.font = graphics.Font()
        script_dir = os.path.dirname(os.path.abspath(__file__))
        font_path = os.path.join(script_dir, 'rpi-rgb-led-matrix', 'fonts', '5x8.bdf')
        self.font.LoadFont(font_path)
        self.textColor = graphics.Color(255, 255, 0)
        self.matrix = RGBMatrix(options=self.options)
        self.offscreen_canvas = self.matrix.CreateFrameCanvas()

    def create_url(self):
        logger.info('create_url begin')
        try: 
            config = configparser.ConfigParser()
            logger.info(os.getcwd())
            config.read('config.ini')
            api_key = config['UserSettings']['api_key']
            stop_id = config['UserSettings']['stop_id']
            url = f'https://bustime.mta.info/api/siri/stop-monitoring.json?key={api_key}&OperatorRef=MTA&MonitoringRef={stop_id}'
            self.url = url

        except Exception as e:
            logger.info('create_url error')
            logger.info(f'{e}')
            messages = self.error_message()
            self.display_message(messages)

    def get_next_bus_time(self):
        logger.info('get_next_bus_time begin')
        try:
            response = requests.get(self.url)
            response.raise_for_status()
            data = response.json()
            return self.parse_bus_times(data)
        
        except requests.exceptions.MissingSchema:
            logger.info('MissingSchema exception')
            return self.error_message()

        except requests.exceptions.InvalidURL:
            logger.info('InvalidURL exception')
            return self.error_message()
        
    def parse_bus_times(self, data):
        logger.info('parse_bus_times begin')
        try:
            messages = []
            current_time = datetime.now().strftime("%H:%M:%S")
            approaching_buses = len(data['Siri']['ServiceDelivery']['StopMonitoringDelivery'][0]['MonitoredStopVisit'])

            if approaching_buses == 0:
                messages.append('No buses')
                messages.append('Check back')
                return messages
            
            for i in range(approaching_buses):
                aimed_arrival_time = data['Siri']['ServiceDelivery']['StopMonitoringDelivery'][0]['MonitoredStopVisit'][i]['MonitoredVehicleJourney']['MonitoredCall']['AimedArrivalTime']
                time_only = aimed_arrival_time.split('T')[1][:8]
                current_hour, current_minute, _ = map(int, current_time.split(':'))
                next_bus_hour, next_bus_minute, _ = map(int, time_only.split(':'))
                minutes_until_next_bus = (next_bus_hour - current_hour) * 60 + (next_bus_minute - current_minute)

                if minutes_until_next_bus == 1:
                    messages.append(f"{minutes_until_next_bus} minute!!!")

                elif minutes_until_next_bus == 0:
                    messages.append('ARRIVING')
                
                elif minutes_until_next_bus < 0:
                    messages.append('DELAY')

                else:
                    messages.append(f'{minutes_until_next_bus} minutes')

            logger.info(messages)
            return messages
        
        except KeyError:
            logger.info('KeyError exception')
            return self.no_buses()
        
    def error_message(self):
        logger.info('error_message begin')
        messages = []
        messages.append('yikes!')
        messages.append('something broke!')
        return messages
    
    def no_buses(self):
        logger.info('no_buses begin')
        messages = []
        messages.append('No buses')
        messages.append('running now')
        return messages

    def display_message(self, messages):
        self.offscreen_canvas.Clear()
        graphics.DrawText(self.offscreen_canvas, self.font, 3, 7, self.textColor, 'M72:')
        for index, message in enumerate(messages[:2]):
            graphics.DrawText(self.offscreen_canvas, self.font, 3, 15 + 8 * index, self.textColor, message)
        self.matrix.SwapOnVSync(self.offscreen_canvas)   

    def after_hours(self):
        logger.info('after_hours begin')
        messages = []
        format = '%H:%M:%S'
        current_time = datetime.now().strftime(format)
        start = datetime.strptime('00:15:00', format)
        end = datetime.strptime('05:30:00', format)
        if start <= current_time <= end:
            messages.append('After Hours')
            messages.append('Until 5:30am')
            return messages

    def run(self):
        self.setup_display()
        self.create_url()
        while True:
            current_message = self.get_next_bus_time()
            self.display_message(current_message)
            time.sleep(60)


if __name__ == "__main__":
        app = BusClock()
        app.run()
    



