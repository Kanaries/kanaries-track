class Config:
    """Config class for kanaries_track"""
    host = "https://log.kanaries.net"
    auth_token = ""
    debug = False
    send = True
    sync_send = False
    max_queue_size = 20 * 1000
    timeout = 15
    max_retries = 5
    proxies = None
    thread = 1
    verify = True
    upload_interval = 1
    upload_size = 100


config = Config()
