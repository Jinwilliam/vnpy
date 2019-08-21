import json
import time

from websocket_server import WebsocketServer

# Called for every client connecting (after handshake)                     
def new_client(client, server):                                                 
    print("New client connected and was given id %d" % client['id'])
	# communicate with json data
    text = json.dumps({'msg': 'Connected to TradeAgent WebSocket Server.'})	
    #server.send_message_to_all(text)
    server.send_message(client, text)
	
# Called for every client disconnecting
def client_left(client, server):                                                
    print("Client({}) disconnected".format(client['id']))
	
# Called when a client sends a message                                          
def message_received(client, server, message):
    if message.startswith('{') and message.endswith('}'):
        message = json.loads(message)
    print('Receiving Client: ', client['id'], client['address'])
    print('Server: ', server.server_address, server.port)
    print(message)

if __name__ == '__main__':                                                                     
    server = WebsocketServer(9443, "0.0.0.0")                                       
    server.set_fn_new_client(new_client)                                            
    server.set_fn_client_left(client_left)                                          
    server.set_fn_message_received(message_received)                                
    server.run_forever()
