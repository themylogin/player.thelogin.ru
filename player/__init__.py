from pyramid.config import Configurator

def main(global_config, **settings):
    config = Configurator(settings=settings)
    config.add_route("file", "/file")
    config.add_route("file_size", "/file_size")
    config.add_route("cover", "/cover")
    config.add_route("lyrics", "/lyrics")
    config.add_route("library", "/library")
    config.add_route("update", "/update")
    config.add_route("player_command", "/player/{command}")
    config.scan()
    return config.make_wsgi_app()
