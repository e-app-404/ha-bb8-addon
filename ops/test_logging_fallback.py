from bb8_core.logging_setup import init_file_handler, logger

h = init_file_handler()
logger.addHandler(h)
logger.warning({"event": "probe"})
print("OK: handler constructed")
