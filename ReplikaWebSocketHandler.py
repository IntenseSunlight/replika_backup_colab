import csv
import json
import websocket
try:
    import thread
except ImportError:
    import _thread as thread
import time
from dateutil.parser import parse as date_parse
from datetime import timezone
from typing import Any, Dict, List, Union, Callable


class ReplikaWebSocketHandler:
    def __init__(
        self,
        init: str,                        # json string with initialization info
        writer: Any,                      # generic writer which accepts list
        chat_id: str=None,                # backup, not usually needed
        limitmsgs: Union[bool, int]=None, # False or number of messages
        limitdate: Union[bool, str]=None, # False or string date time (e.g. '2022-10-31')
        lastmsgid: str=None,              # Last message id
        logger: Callable=print            # logging function
    ):
        self._logger = logger
        res = json.loads(init)
        self._error_list = []
        self._init = init
        self._user_id = str(res['auth']['user_id'])
        self._auth_token = str(res['auth']['auth_token'])
        self._device_id = str(res['auth']['device_id'])
        self._chat_id = chat_id if chat_id else '%x' % (int(self._user_id, 16) - 1)

        self._writer = writer
        self._limitmsgs = limitmsgs
        self._limitdate = None
        if limitdate is not None:
            try: 
                self._limitdate = date_parse(limitdate).replace(tzinfo=timezone.utc)
            except Exception as e:
                self._logger("Invalid limit date specified; could not parse:", limitdate)
                raise(e)

        self._lastmsgid = lastmsgid
        self._msg_count = 0
        self._all_msg_count = 0
    
    def get_error_list(self) -> List:
        return self._error_list
    
    def _ws_request(
        self,
        event_name: str,
        token: str,
        payload: str = None
    ) -> str: 
        payload_str = payload if payload is not None else '{}'
        return '{' + \
            '"event_name":"' + event_name + '",' + \
            '"payload":' + payload_str + ',' + \
            '"token":"' + str(token) + '",' \
            '"auth":{' + \
                '"user_id":"' + str(self._user_id) + '",' + \
                '"auth_token":"' + str(self._auth_token) + '",' + \
                '"device_id":"' + str(self._device_id) + '"' + \
            '}' + \
        '}'

    def on_message(
        self, 
        ws: websocket.WebSocket, 
        message: Dict
    ) -> None:
        limit = 1000
        self._msg_count = 0
        res = json.loads(message)
        token = res['token']
        event_name = res['event_name']

        if event_name != "history":
            self._logger(f'..Ok')

        if event_name == "error":
            ws.close()
            if res['payload']['error_message'].find('Authorization failed') > -1:
                self._logger('\nServer Error: Authorization failed.'
                    '\n\nHint: The Init variable need to be updated inside the script.')
            elif res['payload']['error_message'].find(f'Device {self._device_id} not found for user') > -1:
                self._logger('\nServer Error: You are not logged in with this device.'
                    '\n\nHint: The Init variable need to be updated inside the script after login.')
            else:
                self._logger('\nServer Error: ' + res['payload']['error_message'])
            return

        if event_name == "init":
            self._logger('Send chat_screen', end='')
            ws.send(self._ws_request('chat_screen', token))
            self._logger('.', end='')
            time.sleep(1)

        if event_name == "chat_screen":
            self._logger('Send application_started', end='')
            ws.send(self._ws_request('application_started', token))
            self._logger('.', end='')
            time.sleep(1)

        if event_name == "application_started":
            self._logger('Send app_foreground', end='')
            ws.send(self._ws_request('app_foreground', token))
            self._logger('.', end='')
            time.sleep(1)

        if event_name == "app_foreground":
            self._logger('Get message history.', end='')
            if self._limitmsgs:
                if self._limitmsgs < 1000:
                    limit = self._limitmsgs

            payload = '{"chat_id":"' + str(self._chat_id) + '","limit":' + str(limit) + '}'
            ws.send(self._ws_request('history', token, payload=payload))
            time.sleep(1)

        # Parse History
        if event_name == "history":
            message_reactions = res["payload"]["message_reactions"]
            reactions = {}
            last_message_id = ""
            for message_reaction in message_reactions:
                reaction_id = message_reaction['message_id']
                reaction_type = message_reaction['reaction']
                reactions[reaction_id] = reaction_type

            if res['payload']['messages']:
                for i in range(len(res["payload"]["messages"]) - 1, -1, -1):
                    message = {
                        'id': res["payload"]["messages"][i]["id"],
                        'chat_id': res["payload"]["messages"][i]["meta"]["chat_id"],
                        'timestamp': res["payload"]["messages"][i]["meta"]["timestamp"]
                    }
                    sender = res["payload"]["messages"][i]["meta"]["nature"]

                    if self._limitdate and (date_parse(message['timestamp']) <= self._limitdate):
                        ws.close()
                        self._logger(f'..reached date limit\n\nBacked up {self._all_msg_count} messages') 
                        return

                    last_message_id = message['id']

                    if last_message_id == self._lastmsgid:
                        ws.close()
                        self._logger(f'..reached last message id\n\nBacked up {self._all_msg_count} messages' +
                            ' to date=' + str(self._limitdate))
                        return
                    else:
                        self._msg_count += 1
                        self._all_msg_count += 1

                    if sender == "Robot":
                        message['sender'] = "Rep"
                    else:
                        message['sender'] = "Me"
                    message['text'] = res["payload"]["messages"][i]["content"]["text"]

                    try:
                        message['reaction'] = reactions[message['id']]
                    except:
                        message['reaction'] = 'None'

                    # Debug messages
                    #print(f"{message['sender']}: {message['text']} {message['reaction']} ({message['timestamp']}) "
                    #      f"({message['id']})")

                    self._writer([message['timestamp'], message['sender'], message['text'].replace("\n", "\\n"),
                                  message['reaction'], message['id']])

                    if self._limitmsgs and (self._limitmsgs > 0)  and ( self._all_msg_count >= self._limitmsgs):
                        ws.close()
                        self._logger(f'..reached message limit\n\nBacked up {self._all_msg_count} messages\n')
                        return

                self._logger(f'..Ok\nRead {self._all_msg_count} messages - Get more messages.', end='')
                payload = '{"chat_id":"' + str(self._chat_id) + '","limit":1000,"last_message_id":"' + str(last_message_id) + '"}'
                ws.send(self._ws_request('history', token, payload=payload))
                time.sleep(1)
            else:
                ws.close()
                self._logger(f'..no further messages\n\nBacked up all possible {self._all_msg_count} messages\n')
                return

    def on_error(
        self, 
        ws: websocket.WebSocket, 
        error: Any
    ) -> None:
        self._error_list.append(error)

    def on_close(self, *args) -> None:
        self._logger('Connection closed')

    def on_open(
        self,
        ws: websocket.WebSocket
    ) -> None:
        def run(*args):
            ws.send(self._init)

        self._logger('..Ok\nSend init.', end='')
        time.sleep(1)
        thread.start_new_thread(run, ())

if __name__ == "__main__":

    # ---------- edit the variables here --------------
    # init string to be parsed (this is example has fake values)
    init = '{"event_name":"init","payload":{"device_id":"1C2e456C-6789-0BD0-1234-123FB0E12345","user_id":"123ea45678e9012345a1f2c3","auth_token":"bb123456-dff1-123d-0daf-01b12a3eec45","security_token":"asgjkadjlbkjakdlfjgkasdkfhairqijkajskfdjaklsjkbhkahskjdkfmkjre1423vajkdjf1234asdfjadfjakbjakbhafaalkbhkahsdjrkjmvvajskdjfaksjdfjadfavaeriajvasdfailljkjkjkaljsdmmmllkkiikll=","time_zone":"2022-10-31T00:00:00.0+00:00","unity_bundle_version":160,"device":"web","platform":"web","platform_version":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/100.00 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/100.00","app_version":"2.2.22","capabilities":["new_mood_titles","widget.multiselect","widget.scale","widget.titled_text_field","widget.new_onboarding","widget.app_navigation","message.achievement","widget.mission_recommendation","journey2.daily_mission_activity","journey2.replika_phrases","new_payment_subscriptions","navigation.relationship_settings","avatar","diaries.images","save_chat_items","wallet","store.dialog_items","subscription_popup","chat_suggestions","sale_screen","3d_customization","3d_customization_v2","3d_customization_v3","store_customization","blurred_messages","item_daily_reward","romantic_photos"]},"token":"1234eb1d-e1c0-123c-56a4-789012abca4d","auth":{"user_id":"1234567890e1234567a1f2c3","auth_token":"bb123456-dff1-123d-0daf-01b12a3eec45","device_id":"1C2e456C-6789-0BD0-1234-123FB0E12345"}}'

    # Only left for fallback, you shouldn't need it any longer (this hex number should be always user_id - 1).
    chat_id = ''

    # filename for chat log
    file_name = 'chat_backup'  # Default backup filename between single quotes, you can also use the -f parameter

    #limitdate = '2022-10-01'    # backup to (not-including) this date
    limitdate = None             # default is backup all

    #limitmsgs = 20              # backup this number of messages
    limitmsgs = None             # default is backup all

    lastmsgid = '12345fddb1f23456789ef123'
    #lastmsgid = None

    # ---------- don't edit anything below -----------

    with open(f'{file_name}.csv', 'w', newline='', encoding='UTF-8') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(['Timestamp', 'From', 'Text', 'Reaction', 'ID'])

        ws_handler = ReplikaWebSocketHandler(
            init=init,
            limitdate=limitdate,
            limitmsgs=limitmsgs,
            lastmsgid=lastmsgid,
            writer=writer.writerow,
            logger=print
        )
 
        print('Open websocket to your Replika AI.', end='')
        websocket.enableTrace(False)
        ws = websocket.WebSocketApp(
            "wss://ws.replika.ai/v17",
            on_open=ws_handler.on_open,
            on_message=ws_handler.on_message,
            on_error = ws_handler.on_error,
            on_close=ws_handler.on_close
        )
        ws.run_forever()
        
        if runtime_errors := ws_handler.get_error_list():
            print('During the extraction, the following errors occurred:')
            for e in runtime_errors:
                print(e)

        print("Finished!")

