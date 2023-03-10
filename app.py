import websockets
import asyncio
import json
import time, os


class HttpWSSProtocol(websockets.WebSocketServerProtocol):
    rwebsocket = None
    rddata = None
    async def handler(self):
        try:
            request_line, headers = await websockets.http.read_message(self.reader)
            method, path, version = request_line[:-2].decode().split(None, 2)
            #websockets.accept()
        except Exception as e:
            print(e.args)
            self.writer.close()
            self.ws_server.unregister(self)

            raise

        # TODO: Check headers etc. to see if we are to upgrade to WS.
        if path == '/ws':
            # HACK: Put the read data back, to continue with normal WS handling.
            self.reader.feed_data(bytes(request_line))
            self.reader.feed_data(headers.as_bytes().replace(b'\n', b'\r\n'))

            return await super(HttpWSSProtocol, self).handler()
        else:
            try:
                return await self.http_handler(method, path, version)
            except Exception as e:
                print(e)
            finally:

                self.writer.close()
                self.ws_server.unregister(self)


    async def http_handler(self, method, path, version):
        response = ''
        try:

            googleRequest = self.reader._buffer.decode('utf-8')
            googleRequestJson = json.loads(googleRequest)
            ESPparameters = {}
            command = googleRequestJson['request']['intent']['slots']
            if 'value' in command['question'].keys():
                    ESPparameters['query'] = '?'
            else:
                ESPparameters['query'] = 'cmd'

            if 'open' in command['state']['value']:
                ESPparameters['state'] = command['state']['value']
            elif 'close' in command['state']['value']:
                ESPparameters['state'] = command['state']['value']

            ESPparameters['instance'] = command['instance']['value']
            # {"instance": "1", "state": "open", "query":"?"}
            # {"instance": "both", "state": "close", "query":"cmd"}


            # # send command to ESP over websocket
            if self.rwebsocket== None:
                print("Device is not connected!")
                return
            #await self.rwebsocket.send(json.dumps(googleRequestJson))
            await self.rwebsocket.send(json.dumps(ESPparameters))
            #wait for response and send it back to Alexa as is
            self.rddata = await self.rwebsocket.recv()

            response = '\r\n'.join([
                'HTTP/1.1 200 OK',
                'Content-Type: text/json',
                '',
                ''+self.rddata+'',
            ])
        except Exception as e:
            print(e)
        self.writer.write(response.encode())

def updateData(data):
    HttpWSSProtocol.rddata = data

async def ws_handler(websocket, path):
    game_name = 'g1'
    try:
        HttpWSSProtocol.rwebsocket = websocket
        await websocket.send(json.dumps({'event': 'OK'}))
        data ='{"empty":"empty"}'
        while True:
            data = await websocket.recv()
            updateData(data)
    except Exception as e:
        print(e)
    finally:
        print("")



port = int(os.getenv('PORT', 80))#5687
start_server = websockets.serve(ws_handler, '', port, klass=HttpWSSProtocol)
# logger.info('Listening on port %d', port)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()

