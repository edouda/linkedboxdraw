#usefull explantions pasted from https://realpython.com/python-sockets/#communication-breakdown
import re
import os
import json
import socket
from subprocess import Popen, PIPE, check_output, CalledProcessError
import base64

#host can be a hostname, IP address, or empty string. If an IP address is used, host should
#be an IPv4-formatted address string. The IP address 127.0.0.1 is the standard IPv4 address
#for the loopback interface, so only processes on the host will be able to connect to the server.
#If you pass an empty string, the server will accept connections on all available IPv4 interfaces.
HOST, PORT = '', 8080

#https://docs.python.org/fr/3/howto/sockets.html
#INET:IPV4, STREAM:TCP
listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
listen_socket.bind((HOST, PORT))
#l'argument passé à listen indique à la bibliothèque de connecteurs que nous voulons
#mettre en file d'attente jusqu'à 5 (1 ici) requêtes de connexion (le maximum normal) avant
#de refuser les connexions externes. Si le reste du code est écrit correctement, cela devrait suffire.
listen_socket.listen(1)
print ('Serving HTTP on port %s ...' % PORT)
while True:
    # accept() blocks and waits for an incoming connection. When a client connects, it returns a new socket
    # object representing the connection and a tuple holding the address of the client. The tuple will contain
    # (host, port) for IPv4 connections or (host, port, flowinfo, scopeid) for IPv6.
    # One thing that’s imperative to understand is that we now have a new socket object from accept(). This is
    # important since it’s the socket that you’ll use to communicate with the client. It’s distinct from the
    # listening socket that the server is using to accept new connections.
    # To see the current state of sockets on your host, use netstat -an
    client_connection, client_address = listen_socket.accept()
    # The bufsize argument of 2048 used below is the maximum amount of data to be received at once. 
    # It doesn’t mean that recv() will return 2048 bytes.
    request = client_connection.recv(2048)
    #Lorsqu'un recv renvoie 0 octet, cela signifie que l'autre partie a fermé (ou est en train de fermer)
    #la connexion. Vous ne recevrez plus de données sur cette connexion. Jamais
    #if len(request)==0:
    #    continue
    print(str(request))
    m1 = re.search(r'GET /getFilter\?([^ ]*) HTTP', str(request))
    m2 = re.search(r'GET /getReducedEdges\?data=([^ ]*) HTTP', str(request))    

    try:
        if m1:
            data = m1.group(1)
            nr_rects = int(data[:3], 16)
            print('nr_rects')
            print(str(nr_rects))
            rectdim = data[3:3+nr_rects*6]
            nr_links = int(data[3+nr_rects*6:3+nr_rects*6+3],16)
            print('nr_links')
            print(str(nr_links))
            links = data[3+nr_rects*6+3:3+nr_rects*6+3+nr_links*6]
            filtre = data[3+nr_rects*6+3+nr_links*6:]
            print(rectdim)
            print(links)
            print(filtre)

        #"http_get_param":"01408d0280a203804006807807808d03810b04804708804e0480d304808505806a06806907803903803f04809a0580620380700380700480320380c407801700100e00200e00200500300400501100600e00600500700000701000800900900f00a01200a01000a00900b00d00c00e00e00701000301100701300a01300701300801300b"
        #http://localhost:8080/getFilter?0110af0880940180550180b00180940280850580a10880a20880940380b70180940180c40d811118808603807806806303807805801200300100c00b00c00800e00800d00800a00800a00900100000700800700500700600700200700100700200900700f00801000f002004ffff1
        #http://localhost:8080/getFilter?01a04e06807f08808510807104808d0380630180860180860180710180b618807801809401806301809401807f0280780380a90580550180470180710380780580710180a901806a02808d02807107802201000201001301401601401500e00900e00d01700401901501901601901801800400900800900600900700900a00900b00900400901000900400900400900f00901400900200900e00901900900000900c000002000001002001003004004000004002006005ffffff3

            command=['Release/latuile', '--rectdim', rectdim, '--links', links, '--filter', filtre, '--reqkind', 'getFilter']
            print(str(command))
            json1 = check_output(command).decode("ascii")
            
            rectdim = [rectdim[6*i:6*i+6] for i in range(nr_rects)]
            print('rectdim')
            print(str(rectdim))
            edges = [(int(links[6*i:6*i+3],16), int(links[6*i+3:6*i+6],16)) for i in range(nr_links)]
            print('links')
            print(str(edges))

            data = json.loads(json1)
            for context in data['contexts']:
                frame = context['frame']
                print('frame')
                print(str(frame))
                frame="{:04x}{:04x}{:04x}{:04x}".format(frame['left'],frame['right'],frame['top'],frame['bottom'])
                print('frame')
                print(frame)
                id_x_y = [(translatedBoxes['id'], translatedBoxes['translation']['x'], translatedBoxes['translation']['y']) for translatedBoxes in context['translatedBoxes']]
                print('id_x_y')
                print(str(id_x_y))
                translations = "".join("{:03x}{:03x}".format(x,y) for id,x,y in id_x_y)
                print(translations)

                idmap={}
                for id,x,y in id_x_y:
                    idmap[id] = len(idmap)
                print('idmap')
                print(idmap)

                reverse_idmap = {v:k for k,v in idmap.items()}
                print('reverse_idmap')
                print(reverse_idmap)

                rectdim_ = "".join([rectdim[id] for id,x,y in id_x_y])
                print('rectdim_')
                print(rectdim_)
                assert(len(rectdim_)==len(translations))
                print('translations')
                print(translations)

                links_ = "".join(["{:02x}{:02x}".format(idmap[s],idmap[t]) for s,t in edges if s in idmap and t in idmap])
                print('links_')
                print(links_)

                command=['Release/bombix','--frame', frame,'--rectdim', rectdim_,'--translations', translations,'--links', links_]
                print(str(command))
                json2 = check_output(command).decode("ascii")
                print('json2')
                print(json2)
                
                polylines = json.loads(json2)

                reduced_edges=[{"from":polyline["from"], "to": polyline["to"]} for polyline in polylines]
                print("reduced_edges=" + json.dumps(reduced_edges))
                context['reduced_edges'] = reduced_edges
                
                for polyline in polylines:
                    for u in ['from','to']:
                        polyline[u] = reverse_idmap[ polyline[u] ]
                context['links'] = polylines

            print('contexts')
            print(json.dumps(data))

            http_response = bytearray(json.dumps(data),'ascii')
            client_connection.sendall(b'HTTP/1.0 200 OK\r\nAccess-Control-Allow-Origin:*\r\nAccess-Control-Allow-Headers: Origin, X-Requested-With, Content-Type, Accept\r\nContent-Length: %d\r\nContent-Type: text/html; charset=UTF-8\r\n\r\n%s\r\n' % (len(http_response), http_response))
#            client_connection.close()

        elif m2:
            data = m2.group(1)
            print(data)
            missing_padding = len(data) % 4
            if missing_padding != 0:
                data += '='* (4 - missing_padding)
            data = base64.b64decode(data)
            print(data)
            data = json.loads(data.decode('utf-8'))
            rectdim = "".join("{:03x}{:03x}".format(rec['right']-rec['left'],rec['bottom']-rec['top']) for rec in data['rectangles'])
            print('rectdim')
            print(rectdim)
            translations = "".join("{:03x}{:03x}".format(rec['left'],rec['top']) for rec in data['rectangles'])
            print('translations')
            print(translations)
            links = "".join(["{:02x}{:02x}".format(edge['from'],edge['to']) for edge in data['reduced_edges']])
            print('links')
            print(links)
            frame = data['frame']
            frame = "{:04x}{:04x}{:04x}{:04x}".format(frame['left'],frame['right'],frame['top'],frame['bottom'])
            print('frame')
            print(frame)
            command=['Release/bombix','--frame', frame,'--rectdim', rectdim,'--translations', translations,'--links', links]
            print(str(command))
            json2 = check_output(command).decode("ascii")
            print('json2')
            print(json2)
            
            http_response = bytearray(json2,'ascii')
            client_connection.sendall(b'HTTP/1.0 200 OK\r\nAccess-Control-Allow-Origin:*\r\nAccess-Control-Allow-Headers: Origin, X-Requested-With, Content-Type, Accept\r\nContent-Length: %d\r\nContent-Type: text/html; charset=UTF-8\r\n\r\n%s\r\n' % (len(http_response), http_response))
#            client_connection.close()
            
    except CalledProcessError as e:
        http_response = bytearray(e.output,'ascii')
        client_connection.sendall(b'HTTP/1.0 200 OK\r\nAccess-Control-Allow-Origin:*\r\nAccess-Control-Allow-Headers: Origin, X-Requested-With, Content-Type, Accept\r\nContent-Length: %d\r\nContent-Type: text/html; charset=UTF-8\r\n\r\n%s\r\n' % (len(http_response), http_response))
        client_connection.close()
        print(e.output)
    except ValueError:
        http_response = bytearray("Could not convert data to an integer.",'ascii')
        client_connection.sendall(b'HTTP/1.0 200 OK\r\nAccess-Control-Allow-Origin:*\r\nAccess-Control-Allow-Headers: Origin, X-Requested-With, Content-Type, Accept\r\nContent-Length: %d\r\nContent-Type: text/html; charset=UTF-8\r\n\r\n%s\r\n' % (len(http_response), http_response))
        client_connection.close()
        print("Could not convert data to an integer.")            
