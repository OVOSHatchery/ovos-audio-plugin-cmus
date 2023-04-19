from ovos_utils.log import LOG
from ovos_plugin_common_play.ocp.base import OCPAudioPlayerBackend
from py_cmus import cmusCtrl


cmusAudioPluginConfig = {
    "cmus": {
        "type": "ovos_cmus",
        "active": True
    }
}


class OVOScmusService(OCPAudioPlayerBackend):
    def __init__(self, config, bus=None, name='ovos_cmus'):
        super(OVOScmusService, self).__init__(config, bus)
        self.config = config
        self.bus = bus
        self.name = name

        self.index = 0
        self.normal_volume = None
        self.tracks = []
        self.mpc = cmusCtrl()

        self.mpc.on_media_started = self.handle_media_started
        self.mpc.on_media_finished = self.handle_media_finished
        self.mpc.on_stderr = self.handle_cmus_error

    # cmus internals
    def handle_cmus_error(self, evt):
        self.ocp_error()

    def handle_media_started(self, evt):
        LOG.debug('cmus playback start')
        self.mpc.playing = True
        if self._track_start_callback:
            self._track_start_callback(self.track_info().get('name', "track"))

    def handle_media_finished(self, evt):
        LOG.debug('cmus playback ended')
        self._now_playing = None
        self.mpc.playing = False
        if self._track_start_callback:
            self._track_start_callback(None)
        self.ocp_stop()

    # audio service
    def supported_uris(self):
        return ['file', 'http', 'https']

    def play(self, repeat=False):
        """ Play playlist using cmus. """
        LOG.debug('cmusService Play')
        self.ocp_start()  # emit ocp state events
        self.mpc.loadfile(self._now_playing)
        self.mpc.playing = True

    def stop(self):
        """ Stop cmus playback. """
        LOG.info('cmusService Stop')
        if self.mpc.playing:
            self.mpc.stop()
            self.ocp_stop()  # emit ocp state events
            return True
        return False

    def pause(self):
        """ Pause cmus playback. """
        if not self.mpc.paused:
            self.mpc.pause()
            self.ocp_pause()  # emit ocp state events

    def resume(self):
        """ Resume paused playback. """
        if self.mpc.paused:
            self.mpc.pause()
            self.ocp_resume()  # emit ocp state events

    def track_info(self):
        """ Extract info of current track. """
        ret = {}
        ret['title'] = self.mpc.get_meta_title()
        ret['artist'] = self.mpc.get_meta_artist()
        ret['album'] = self.mpc.get_meta_album()
        ret['genre'] = self.mpc.get_meta_genre()
        ret['year'] = self.mpc.get_meta_year()
        ret['track'] = self.mpc.get_meta_track()
        ret['comment'] = self.mpc.get_meta_comment()
        return ret

    def get_track_length(self):
        """
        getting the duration of the audio in milliseconds
        """
        return self.mpc.get_time_length() * 1000  # seconds to milliseconds

    def get_track_position(self):
        """
        get current position in milliseconds
        """
        return self.mpc.get_time_pos() * 1000  # seconds to milliseconds

    def set_track_position(self, milliseconds):
        """
        go to position in milliseconds

          Args:
                milliseconds (int): number of milliseconds of final position
        """
        self.mpc.set_property("time_pos", milliseconds / 1000)

    def shutdown(self):
        """
            Shutdown cmus
        """
        self.mpc.destroy()


def load_service(base_config, bus):
    backends = base_config.get('backends', [])
    services = [(b, backends[b]) for b in backends
                if backends[b]['type'] in ["cmus", 'ovos_cmus'] and
                backends[b].get('active', False)]
    instances = [OVOScmusService(s[1], bus, s[0]) for s in services]
    return instances
