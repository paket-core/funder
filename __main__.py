"""Run the PaKeT funding server."""
import bridge
bridge.APP.run('0.0.0.0', bridge.routes.PORT, bridge.webserver.validation.DEBUG)
