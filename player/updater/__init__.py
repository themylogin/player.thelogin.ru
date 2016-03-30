# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import logging
import os
import pyinotify
import Queue
import threading
import time

from themyutils.queue import QueueDemux

__all__ = [b"UpdatersManager"]

logger = logging.getLogger(__name__)



class UpdatersManager(object):
    def __init__(self, directory):
        producer_queue = Queue.Queue()
        self.demux = QueueDemux(producer_queue)

        producer = MusicUpdatesProducer(directory, producer_queue)
        producer.start()

    def add_updater(self, updater):
        updater_thread = UpdaterThread(self.demux.clone(), updater)
        updater_thread.start()


class UpdaterThread(threading.Thread):
    def __init__(self, queue, updater):
        super(UpdaterThread, self).__init__()
        self.daemon = True

        self.queue = queue
        self.updater = updater

    def run(self):
        while True:
            updates = self.queue.get()
            while True:
                try:
                    self.updater.update(updates)
                except:
                    logger.exception("Updater %r failed", self.updater)
                    time.sleep(10)
                else:
                    logger.debug("Updater %r finished processing %r", self.updater, updates)
                    break


class MusicUpdatesProducer(threading.Thread):
    def __init__(self, directory, queue):
        super(MusicUpdatesProducer, self).__init__()
        self.daemon = True

        self.directory = directory
        self.produce_queue = Queue.Queue()
        self.output_queue = queue

        self.watch_manager = pyinotify.WatchManager()
        self.notifier = pyinotify.Notifier(self.watch_manager, self.handle_event)

    def handle_event(self, event):
        logger.debug("Received event: %r", event)

        if event.mask & (pyinotify.IN_CREATE | pyinotify.IN_MOVED_TO):
            if event.dir:
                self.add_watch(event.pathname)

        if event.dir:
            self.emit_update(event.pathname)
        else:
            self.emit_update(event.path)

    def add_watch(self, directory):
        try:
            self.watch_manager.add_watch(directory, pyinotify.IN_CREATE |
                                                    pyinotify.IN_DELETE |
                                                    pyinotify.IN_MOVED_FROM |
                                                    pyinotify.IN_MOVED_TO |
                                                    0)
            for child in os.listdir(directory):
                child_full = os.path.join(directory, child)
                if os.path.isdir(child_full):
                    self.add_watch(child_full)
        except Exception:
            logger.debug("add_watch(%r) failed", directory, exc_info=True)

    def emit_update(self, path):
        path = os.path.relpath(path, self.directory)
        logger.debug("Produce update: %s", path)
        self.produce_queue.put(path)

    def run(self):
        delayer = MusicUpdatesDelayer(self.produce_queue, self.output_queue, 10)
        delayer.start()

        self.add_watch(self.directory)

        while True:
            self.notifier.process_events()
            if self.notifier.check_events():
                self.notifier.read_events()


class MusicUpdatesDelayer(threading.Thread):
    def __init__(self, input_queue, output_queue, delay):
        super(MusicUpdatesDelayer, self).__init__()
        self.daemon = True

        self.input_queue = input_queue
        self.output_queue = output_queue
        self.delay = delay

    def run(self):
        updates = set()
        while True:
            try:
                updates.add(self.input_queue.get(True, self.delay))
            except Queue.Empty:
                changed = True
                while changed:
                    changed = False
                    for path in updates:
                        if path != "":
                            parent = os.path.dirname(path)
                            if parent in updates:
                                logger.debug("Discarding %s update because parent update also exists in batch", path)
                                updates.remove(path)
                                changed = True
                                break

                if updates:
                    logger.info("Emit updates: %r", updates)
                    self.output_queue.put(list(updates))

                    updates.clear()
