import argparse
import asyncio
import websockets
import json
from server_const import Status, RequestType, ENTITY_TYPE

parser = argparse.ArgumentParser(description='Host machine CLI')

parser.add_argument('-u', '--username', type=str, required=True, help='Username')
parser.add_argument('-p', '--password', type=str, required=True, help='Password')
parser.add_argument('-s', '--server-url', type=str, required=True, help="Address of the server")
parser.add_argument('-m', '--max-memory', type=int, required=False, help='Max memory allowed to be stored on the machine')

args = parser.parse_args()

server_url = args.server_url

def createInitJSON(username, password):
    data = {
        "username" : username,
        "password" : password,
        "requestType": RequestType.INIT,
        "entityType": ENTITY_TYPE
    }
    return json.dumps(data)

def createStoreFileResponseJSON(status, message):
    data = {
        "status" : status,
        "message" : message,
        "requestType": RequestType.SAVE_FILE,
        "entityType": ENTITY_TYPE
    }
    return json.dumps(data) 

def createRetrieveFileResponseJSON(status, message, filename):
    try: 
        if status == Status.SUCCESS:
            # only process further if its not already a failure
            with open(filename, 'r') as f:
                content = f.read()
    except Exception as e:
        status = Status.FAIL
        message = f"File could not be opened on the host machine. {str(e)}"
        print(message)
        content = ""
    
    data = {
        "status" : status,
        "message" : message, 
        "responseType": RequestType.RETRIEVE_FILE,
        "entityType": ENTITY_TYPE, 
        "body": content
    }
    
    return json.dumps(data)
    

def parseInitResponse(response):
    try:
        return response['status']
    except Exception as e:
        print("Error " + str(e))

def parseRetrieveRequest(request):
    try:
        return request['filename']
    except Exception as e:
        print("Error: " + str(e))
        raise e
    
def parseStoreRequest(request):
    try: 
        filename = request['filename']
        body = request['body']
        return filename, body
    except Exception as e:
        print("Error: " + str(e))
        raise e
 
    

async def main():
    async with websockets.connect(server_url, max_size=2**27) as websocket:
        # startup and send init message to the server
        init_message = createInitJSON(args.username, args.password)
        await websocket.send(init_message)
        response = await websocket.recv()
        server_status = parseInitResponse(json.loads(response))
        if server_status == Status.FAIL:
            print("Server in bad state. Please try again later.")
            exit(0)
            
        # await for message from server
        while True: 
            msg = websocket.recv() 
            msg_json = json.loads(msg)
            requestType = msg_json['requestType']
            
            if requestType == RequestType.RETRIEVE_FILE:
                # give back file
                filename = parseRetrieveRequest(msg_json)
                response = createRetrieveFileResponseJSON(Status.SUCCESS, "", filename)
                await websocket.send(response)
                
            elif requestType == RequestType.SAVE_FILE:
                filename, body = parseStoreRequest(msg_json)
                status = Status.SUCCESS
                message = ""
                try: 
                    # save file
                    with open(filename, "w") as f:
                        f.write(body)
                except Exception as e:
                    message = str(e)
                    print("Error: " + message)
                    status = Status.FAIL
                response = createStoreFileResponseJSON(status, message)
                await websocket.send(response)
        
        
asyncio.get_event_loop().run_until_complete(main())