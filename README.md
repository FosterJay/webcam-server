# webcam-server

> webcam-server.py is an all-in-one python script that lets you host or connect to a webcam server.

## DEPENDENCIES

### Software Dependencies

Python 2.7 (tested 2.7.12)

OpenCV (pip install opencv-python)


## USAGE

### Hosting A Server

The script uses port 1895 by default.

To allow connections from outside your network, you'll have to port forward to it on your router.

Run `python webcam-server.py -s` in the terminal, with the current working directory set as the location of webcam-server.py.


### Connecting To A Server

Run `python webcam-server.py` or `python webcam-server.py -c`, with the current working directory set as the location of webcam-server.py.
