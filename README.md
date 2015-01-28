# player.thelogin.ru

This is server software for [3G Player](https://github.com/themylogin/3G-Player)

## Prerequisites

Make sure avconv with libmp3lame support is installed

## Configuration

Edit ```development.ini```

## Installation

* ```python setup.py develop```

Easy way:

* ```pserve --reload development.ini```

Proper way:

* UWSGI configuration:

        [uwsgi]
        uid = themylogin
        gid = themylogin
        chmod-socket = 666
        
        master = 1
        processes = 5
        
        virtualenv = /home/themylogin/www/apps/virtualenv
        
        chdir = /home/themylogin/www/apps/player
        paste = config:/home/themylogin/www/apps/player/production.ini

        paste-logger
        enable-threads

        logto = /var/log/uwsgi/player.log

* nginx configuration:

        server {
	        root /home/themylogin/www/apps/player/player/static;
	        server_name player.thelogin.ru;
          
	        location / {
		        try_files $uri @player;
	        }
        
	        location @player {
		        include uwsgi_params;
		        uwsgi_param SCRIPT_NAME '';
		        uwsgi_pass unix:///run/uwsgi/app/player/socket;
		        uwsgi_read_timeout 3600;
		        uwsgi_buffering off;
	        }
        }

## Usage Tips

* Put this into your cron.hourly:

        #!/bin/sh
        curl http://.../update

* Put this into your cron.daily:

        #!/bin/sh
        find /tmp/player.thelogin.ru -mtime +1 -exec rm {} \;
