import os
import os.path
import socket
import subprocess

from ovos_plugin_manager.templates.media import AudioPlayerBackend
from ovos_utils.log import LOG


def program_running(progam):
    p = subprocess.Popen(["pidof", progam], stdout=subprocess.PIPE)
    p.communicate(input=None)
    return p.returncode == 0


class CmusPlayer:
    process_name = "cmus"  # used for pidof
    friendly_name = "cmus"  # used for display in help

    # socket
    def create_socket(self):
        return socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

    def connect_socket(self, socket):
        socket.connect(self.socket_path())

    def send_socket_command(self, command):
        s = self.get_open_socket()
        s.send((command + "\n").encode("ascii"))
        # We never know how much to receive, most of these
        # protocols send very little data back for the commands
        # we use.
        # It's also easier to write both Python 2 and 3 compatible
        # if we convert to unicode strings everywhere.
        # Usually we are getting back ASCII.
        return s.recv(2048).decode('utf-8')

    def get_open_socket(self):
        if hasattr(self, '_socket'):
            return self._socket
        s = self.create_socket()
        self.connect_socket(s)
        self._socket = s
        # We'll leave it to Python to clean this up when
        # the script exits...
        return s

    def socket_path(self):
        for f in [
            os.path.join(os.environ['XDG_RUNTIME_DIR'], 'cmus-socket'),
            os.path.join(os.environ['HOME'], '.cmus', 'socket'),
        ]:
            if os.path.exists(f):
                return f
        raise RuntimeError("cmus is running, but its socket is not found")

    # player
    def is_running(self):
        """
        Returns true if the player program is running.
        Must be implemented (or process_name must be specified)
        """
        return program_running(self.process_name)

    def is_stopped(self):
        return 'status stopped' in self.send_socket_command('status')

    def is_paused(self):
        return 'status paused' in self.send_socket_command('status')

    def is_playing(self):
        return 'status playing' in self.send_socket_command('status')

    def add_path(self, path):
        """Add file/dir/url/playlist"""
        self.send_socket_command(f'add {path}')

    def play(self):
        self.send_socket_command('player-play')

    def pause(self):
        self.send_socket_command("player-pause")

    def unpause(self):
        self.pause()

    def stop(self):
        self.send_socket_command("player-stop")

    def next(self):
        self.send_socket_command("player-next")

    def prev(self):
        self.send_socket_command("player-prev")

    def seek_to_position(self, seconds):
        self.send_socket_command(f"seek {seconds}")

    def seek_forward(self, n=5):
        self.send_socket_command(f"seek +{n}")

    def seek_backward(self, n=5):
        self.send_socket_command(f"seek -{n}")

    def increase_volume(self, n=20):
        self.send_socket_command(f"vol +{n}%")

    def lower_volume(self, n=20):
        self.send_socket_command(f"vol -{n}%")

    def toggle_pause(self):
        """
        Plays if paused, pauses if playing.
        """
        if self.is_paused():
            self.unpause()
        else:
            self.pause()

    def play_pause(self):
        """
        Plays if stopped/paused, pauses if playing.
        """
        if self.is_stopped():
            self.play()
        else:
            self.toggle_pause()


class CmusOCPAudioService(AudioPlayerBackend):
    def __init__(self, config, bus=None):
        super().__init__(config, bus)
        self.index = 0
        self.tracks = []
        self.player = CmusPlayer()

    # audio service
    def supported_uris(self):
        return ['file', 'http', 'https']

    def play(self, repeat=False):
        """ Play playlist using Cmus. """
        LOG.debug('CmusService Play')
        self.player.add_path(self.tracks)
        self.player.play()

    def stop(self):
        """ Stop Cmus playback. """
        LOG.info('CmusService Stop')
        if self.player.is_playing():
            self.player.stop()
            return True
        return False

    def pause(self):
        """ Pause Cmus playback. """
        if not self.player.is_paused():
            self.player.pause()

    def resume(self):
        """ Resume paused playback. """
        if self.player.is_paused():
            self.player.pause()

    def lower_volume(self):
        """Lower volume.

        This method is used to implement audio ducking. It will be called when
        Mycroft is listening or speaking to make sure the media playing isn't
        interfering.
        """
        self.player.lower_volume(30)

    def restore_volume(self):
        """Restore normal volume.

        Called when to restore the playback volume to previous level after
        Mycroft has lowered it using lower_volume().
        """
        self.player.increase_volume(30)

    def set_track_position(self, milliseconds):
        """
        go to position in milliseconds
          Args:
                milliseconds (int): number of milliseconds of final position
        """
        self.player.seek_to_position(milliseconds / 1000)

    def seek_forward(self, seconds=1):
        """Skip X seconds.

        Arguments:
            seconds (int): number of seconds to seek, if negative rewind
        """
        self.player.seek_forward(seconds)

    def seek_backward(self, seconds=1):
        """Rewind X seconds.

        Arguments:
            seconds (int): number of seconds to seek, if negative jump forward.
        """
        self.player.seek_backward(seconds)

    # TODO
    def get_track_length(self):
        """
        getting the duration of the audio in milliseconds
        """

    def get_track_position(self):
        """
        get current position in milliseconds
        """

    def track_info(self):
        """Get info about current playing track.

        Returns:
            dict: Track info containing atleast the keys artist and album.
        """
        ret = {}
        ret['artist'] = ''
        ret['album'] = ''
        return ret
