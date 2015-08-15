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
	        
	        location /player/become_superseeded {
		        try_files $uri @player;
		        allow 192.168.0.3;
		        allow 192.168.0.7;
		        deny all;
	        }
        
	        location @player {
		        include uwsgi_params;
		        uwsgi_param SCRIPT_NAME '';
		        uwsgi_pass unix:///run/uwsgi/app/player/socket;
		        uwsgi_read_timeout 3600;
		        uwsgi_buffering off;
	        }
        }
        
Or, alternatively, if you need logging and it does not work for you (you see ```ImportError: No module named script.util.logging_config``` in uwsgi log), you can use this supervisord configuration:

	[program:player_pserve]
	user=themylogin
	group=themylogin
	directory=/home/themylogin
	environment=HOME="/home/themylogin"
	numprocs=5
	numprocs_start=0
	command=/home/themylogin/virtualenv/stable/bin/pserve /home/themylogin/apps/player/production.ini http_port=5673%(process_num)d
	process_name=%(program_name)s-%(process_num)d
	autostart=true
	autorestart=true
	redirect_stderr=true
	
and this nginx configuration:

	server {
		root /home/themylogin/www/apps/player/player/static;
		server_name player.thelogin.ru;
	
		location / {
			try_files $uri @player;
		}
	
		location /player/become_superseeded {
			try_files $uri @player;
			allow 192.168.0.3;
			allow 192.168.0.7;
			deny all;
		}
	
		location @player {
	        proxy_buffering off;
	        proxy_read_timeout 3600s;
			proxy_pass http://player_pserve;
	
			add_header Access-Control-Allow-Methods "GET, OPTIONS";
			add_header Access-Control-Allow-Origin "*";
		}
	}
	
	upstream player_pserve {
		server 127.0.0.1:56730;
		server 127.0.0.1:56731;
		server 127.0.0.1:56732;
		server 127.0.0.1:56733;
		server 127.0.0.1:56734;
	}

You may also want to enable library (and MPD!) auto-update:

	[program:player_updates_manager]
	user=themylogin
	group=themylogin
	directory=/home/themylogin
	environment=HOME="/home/themylogin"
	command=/home/themylogin/virtualenv/stable/bin/player_updates_manager /home/themylogin/apps/player/production.ini
	autostart=true
	autorestart=true
	redirect_stderr=true

## Usage Tips

* Put this into your cron.hourly:

        #!/bin/sh
        curl http://.../update

* Put this into your cron.daily:

        #!/bin/sh
        find /tmp/player.thelogin.ru -mtime +1 -exec rm {} \;
