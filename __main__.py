"""Run the PaKeT funding server."""
import funder
funder.APP.run('0.0.0.0', funder.routes.PORT, funder.webserver.validation.DEBUG)
