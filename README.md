# webcam-server
webcam-server.py is an all-in-one python script that lets you host or connect to a webcam server.
It's fairly simple to use, and requires only one dependency.

======================================================

1. Dependencies
	1.1 Software Dependencies
	1.2 Python Dependencies

2. Usage
	2.1 Hosting a server
		2.1a Terminal
	2.2 Connecting to a server

======================================================

1. DEPENDENCIES
	1.1 Software Dependencies
		- Python 2.7 (tested 2.7.12)

	1.2 Python Dependencies
		- OpenCV (pip install opencv-python)

2. USAGE
	2.1 Hosting A Server
		- The script uses port 1895 by default.
		- To allow connections from outside your network, you'll have to port forward to it on your router.

		2.1a Terminal
			Run "python webcam-server.py -s" in the terminal, with the current working directory set as the location of webcam-server.py.

	2.2 Connecting To A Server
		Run "python webcam-server.py" or "python webcam-server.py -c", with the current working directory set as the location of webcam-server.py.
