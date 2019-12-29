import sys
import asyncio
from argparse import ArgumentParser

import qth
import pychromecast

from .version import __version__


loop = asyncio.get_event_loop()


class ChromecastDevice(object):
    """A connection to a particular chromecast device."""
    
    def __init__(self, loop, qth_client, qth_path_prefix, chromecast):
        self._loop = loop
        self._client = qth_client
        self._chromecast = chromecast
        
        self._last_app_name = object()
        self._last_app_icon = object()
        self._last_volume = object()
        self._last_title = object()
        self._last_thumbnail = object()
        self._last_playing = object()
        
        self._app_name_path = "{}app_name".format(qth_path_prefix)
        self._app_icon_path = "{}app_icon".format(qth_path_prefix)
        
        self._volume_path = "{}volume".format(qth_path_prefix)
        self._volume_increment_path = "{}/increment".format(self._volume_path)
        self._volume_decrement_path = "{}/decrement".format(self._volume_path)
        
        self._title_path = "{}title".format(qth_path_prefix)
        self._thumbnail_path = "{}thumbnail".format(qth_path_prefix)
        
        self._playing_path = "{}playing".format(qth_path_prefix)
        self._play_path = "{}play".format(qth_path_prefix)
        self._pause_path = "{}pause".format(qth_path_prefix)
        self._stop_path = "{}stop".format(qth_path_prefix)
        
        self._next_path = "{}next".format(qth_path_prefix)
        self._previous_path = "{}previous".format(qth_path_prefix)
        
        self._seek_path = "{}seek".format(qth_path_prefix)
        self._seek_relative_path = "{}seek_relative".format(qth_path_prefix)
        
        self._loop.create_task(self.async_init())
    
    async def async_init(self):
        await self._loop.run_in_executor(None, self._chromecast.wait)
        
        # Register all Qth endpoints
        await asyncio.gather(
            self._client.register(
                self._app_name_path,
                qth.PROPERTY_ONE_TO_MANY,
                description="Name of the app currently running on this chromecast.",
                delete_on_unregister=True,
            ),
            self._client.register(
                self._app_icon_path,
                qth.PROPERTY_ONE_TO_MANY,
                description="URL of icon for the app currently running on this chromecast.",
                delete_on_unregister=True,
            ),
            self._client.register(
                self._volume_path,
                qth.PROPERTY_ONE_TO_MANY,
                description="Current volume level. A float in the range 0.0 to 1.0",
                delete_on_unregister=True,
            ),
            self._client.register(
                self._volume_increment_path,
                qth.EVENT_MANY_TO_ONE,
                description="Increment the volume (in the range 0.0 to 1.0)",
            ),
            self._client.register(
                self._volume_decrement_path,
                qth.EVENT_MANY_TO_ONE,
                description="Decrement the volume (in the range 0.0 to 1.0)",
            ),
            self._client.register(
                self._title_path,
                qth.PROPERTY_ONE_TO_MANY,
                description="Title of currently playing media item (if any).",
                delete_on_unregister=True,
            ),
            self._client.register(
                self._thumbnail_path,
                qth.PROPERTY_ONE_TO_MANY,
                description="URL of thumbnail for currently playing media item (if any).",
                delete_on_unregister=True,
            ),
            self._client.register(
                self._playing_path,
                qth.PROPERTY_ONE_TO_MANY,
                description="Current playback state. Boolean.",
                delete_on_unregister=True,
            ),
            self._client.register(
                self._play_path,
                qth.EVENT_MANY_TO_ONE,
                description="Start playing the current item.",
            ),
            self._client.register(
                self._pause_path,
                qth.EVENT_MANY_TO_ONE,
                description="Pause the current item.",
            ),
            self._client.register(
                self._stop_path,
                qth.EVENT_MANY_TO_ONE,
                description="Stop the current item.",
            ),
            self._client.register(
                self._next_path,
                qth.EVENT_MANY_TO_ONE,
                description="Skip to the next track.",
            ),
            self._client.register(
                self._previous_path,
                qth.EVENT_MANY_TO_ONE,
                description="Skip to the previous track.",
            ),
            self._client.register(
                self._seek_path,
                qth.EVENT_MANY_TO_ONE,
                description="Seek to a particular position within a track (takes a float in seconds)",
            ),
            self._client.register(
                self._seek_relative_path,
                qth.EVENT_MANY_TO_ONE,
                description="Seek forward or backward the specified number of seconds",
            ),
            loop=self._loop,
        )
        
        # Register callbacks
        await asyncio.gather(
            self._client.watch_property(self._volume_path, self.on_volume_change),
            self._client.watch_event(self._volume_increment_path, self.on_volume_increment),
            self._client.watch_event(self._volume_decrement_path, self.on_volume_decrement),
            self._client.watch_property(self._playing_path, self.on_playing_change),
            self._client.watch_event(self._play_path, self.on_play),
            self._client.watch_event(self._pause_path, self.on_pause),
            self._client.watch_event(self._stop_path, self.on_stop),
            self._client.watch_event(self._next_path, self.on_next),
            self._client.watch_event(self._previous_path, self.on_previous),
            self._client.watch_event(self._seek_path, self.on_seek),
            self._client.watch_event(self._seek_relative_path, self.on_seek_relative),
            loop=self._loop,
        )
        
        # Register for device state changes
        self._chromecast.register_status_listener(self)  # -> new_cast_status
        self._chromecast.media_controller.register_status_listener(self)  # -> new_media_status
        
        # Report initial state
        await asyncio.gather(
            self.on_new_cast_status(self._chromecast.status),
            self.on_new_media_status(self._chromecast.media_controller.status),
        )
    
    async def on_volume_change(self, path, new_volume):
        new_volume = max(0.0, min(1.0, new_volume))
        
        await self._loop.run_in_executor(
            None,
            self._chromecast.set_volume,
            new_volume,
        )
    
    async def on_volume_increment(self, path, delta):
        if delta is None:
            delta = 0.01
        
        volume = self._chromecast.status.volume_level
        volume += delta
        
        await self.on_volume_change(path, volume)
    
    async def on_volume_decrement(self, path, delta):
        if delta is None:
            delta = 0.01
        
        await self.on_volume_increment(path, -delta)
    
    async def on_playing_change(self, path, new_playing):
        if new_playing:
            await self.on_play(path, None)
        else:
            await self.on_pause(path, None)
    
    async def on_play(self, path, value):
        await self._loop.run_in_executor(
            None,
            self._chromecast.media_controller.play,
        )
    
    async def on_pause(self, path, value):
        await self._loop.run_in_executor(
            None,
            self._chromecast.media_controller.pause,
        )
    
    async def on_stop(self, path, value):
        await self._loop.run_in_executor(
            None,
            self._chromecast.media_controller.stop,
        )
    
    async def on_next(self, path, value):
        await self._loop.run_in_executor(
            None,
            self._chromecast.media_controller.queue_next,
        )
    
    async def on_previous(self, path, value):
        await self._loop.run_in_executor(
            None,
            self._chromecast.media_controller.queue_prev,
        )
    
    async def on_seek(self, path, new_position):
        await self._loop.run_in_executor(
            None,
            self._chromecast.media_controller.seek,
            new_position,
        )
    
    async def on_seek_relative(self, path, delta):
        position = self._chromecast.media_controller.status.adjusted_current_time
        position += delta or 0.0
        
        await self.on_seek(path, position)
    
    def new_cast_status(self, status):
        self._loop.call_soon_threadsafe(
            self._loop.create_task,
            self.on_new_cast_status(status),
        )
    
    async def on_new_cast_status(self, status):
        to_run = []
        
        if status.display_name != self._last_app_name:
            to_run.append(self._client.set_property(self._app_name_path, status.display_name))
            self._last_app_name = status.display_name
        
        if status.icon_url != self._last_app_icon:
            to_run.append(self._client.set_property(self._app_icon_path, status.icon_url))
            self._last_app_icon = status.icon_url
        
        volume = status.volume_level if not status.volume_muted else 0.0
        if volume != self._last_volume:
            to_run.append(self._client.set_property(self._volume_path, volume))
            self._last_volume = volume
        
        if to_run:
            await asyncio.gather(*to_run, loop=self._loop)
    
    def new_media_status(self, status):
        self._loop.call_soon_threadsafe(
            self._loop.create_task,
            self.on_new_media_status(status),
        )
    
    async def on_new_media_status(self, status):
        to_run = []
        
        if status.title != self._last_title:
            to_run.append(self._client.set_property(self._title_path, status.title))
            self._last_title = status.title
        
        thumbnail = status.images[0][0] if len(status.images) >= 1 else None
        if thumbnail != self._last_thumbnail:
            to_run.append(self._client.set_property(self._thumbnail_path, thumbnail))
            self._last_thumbnail = thumbnail
        
        if status.player_is_playing != self._last_playing:
            to_run.append(self._client.set_property(self._playing_path, status.player_is_playing))
            self._last_playing = status.player_is_playing
        
        if to_run:
            await asyncio.gather(*to_run, loop=self._loop)

class QthChromecast(object):
    
    def __init__(self, loop, qth_client, qth_path_prefix):
        self._loop = loop
        self._client = qth_client
        self._prefix = qth_path_prefix
        
        # {name: pychromecast.Chromecast}
        self._chromecasts = {}
        
        self._stop_discovery = pychromecast.get_chromecasts(
            blocking=False,
            callback=lambda cc: self._loop.call_soon_threadsafe(
                self.on_chromecast_discovered,
                cc,
            )
        )
    
    def on_chromecast_discovered(self, chromecast):
        # Ignore rediscovery of existing device
        name = chromecast.name.replace(" ", "_").lower()
        
        if name not in self._chromecasts:
            self._chromecasts[name] = ChromecastDevice(
                self._loop,
                self._client,
                "{}{}/".format(self._prefix, name),
                chromecast,
            )
    
    
def main():
    parser = ArgumentParser(
        description="Control Chromecast devices on the local network")
    parser.add_argument(
        "--qth-path-prefix", "-p",
        default="sys/chromecast/",
        help="Qth path prefix."
    )
    
    parser.add_argument("--host", "-H", default=None,
                        help="Qth server hostname.")
    parser.add_argument("--port", "-P", default=None, type=int,
                        help="Qth server port.")
    parser.add_argument("--keepalive", "-K", default=10, type=int,
                        help="MQTT Keepalive interval (seconds).")
    parser.add_argument("--version", "-V", action="version",
                        version="%(prog)s {}".format(__version__))
    args = parser.parse_args()
    
    client = qth.Client(
        "qth_chromecast", "Chromecast control",
        loop=loop,
        host=args.host,
        port=args.port,
        keepalive=args.keepalive,
    )
    
    qth_cc = QthChromecast(loop, client, args.qth_path_prefix)
    loop.run_forever()

if __name__ == "__main__":
    main()
