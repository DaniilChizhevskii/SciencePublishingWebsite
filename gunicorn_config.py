import multiprocessing

workers = multiprocessing.cpu_count() * 2 + 1
bind = 'unix:books.sock'
umask = 0o007
reload = True

accesslog = '-'
errorlog = '-'
