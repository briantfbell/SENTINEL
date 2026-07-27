"""AudioPlayer protocol and implementations."""

from sentinel.audio.aplay_player import AplayAudioPlayer
from sentinel.audio.errors import AudioError
from sentinel.audio.mock import MockAudioPlayer, PlaybackCall
from sentinel.audio.player import AudioPlayer

__all__ = [
    "AplayAudioPlayer",
    "AudioError",
    "AudioPlayer",
    "MockAudioPlayer",
    "PlaybackCall",
]
