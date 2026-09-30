import time


class AudioMonitor:
    """Monitors audio input, background noise spikes, and abnormal sound activities."""

    def __init__(self, spike_threshold=65.0, sustained_frames=4):
        self.spike_threshold = spike_threshold
        self.sustained_frames = sustained_frames
        self.history = []
        self.last_spike_time = 0

    def process_volume(self, volume_db: float) -> dict:
        """
        Evaluates audio level (in dB or relative percentage 0-100).
        Returns:
            dict with:
                - volume: float
                - status: 'NORMAL', 'MODERATE_NOISE', 'ABNORMAL_NOISE', 'TALKING_DETECTED'
                - is_anomaly: bool
                - confidence: float
        """
        now = time.time()
        self.history.append((now, volume_db))

        # Keep last 10 seconds of history
        self.history = [(t, v) for (t, v) in self.history if now - t <= 10.0]

        is_anomaly = False
        status = 'NORMAL'
        confidence = 0.0

        if volume_db > self.spike_threshold:
            # Check if this high volume is sustained
            recent_high = [v for (t, v) in self.history if now - t <= 2.0 and v > self.spike_threshold]
            if len(recent_high) >= self.sustained_frames:
                status = 'TALKING_DETECTED'
                is_anomaly = True
                confidence = min(1.0, round((volume_db - self.spike_threshold) / 25.0 + 0.6, 2))
            else:
                status = 'NOISE_SPIKE'
                is_anomaly = False
                confidence = 0.4
        elif volume_db > (self.spike_threshold - 15.0):
            status = 'MODERATE_NOISE'
            confidence = 0.3

        return {
            'volume': round(float(volume_db), 1),
            'status': status,
            'is_anomaly': is_anomaly,
            'confidence': confidence
        }

    def reset(self):
        self.history = []
